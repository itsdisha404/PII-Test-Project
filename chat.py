from __future__ import annotations
import json
from typing import List, Optional
from openai import OpenAI
from config import get_settings
from eligibility import ELIGIBILITY_TOOL, check_eligibility
from logs import masking_log
from memory import SessionMemory

SYSTEM_PROMPT = (
    "You are an eligibility assistant. Your job is to determine whether a "
    "user is eligible, which requires their name, age, and email. "
    "Collect these one at a time, strictly in this order: name first, "
    "then age, then email. If you don't yet have all three -- including "
    "at the very start of a new conversation, before the user has said "
    "anything -- briefly introduce yourself and ask only for the next "
    "missing item in that order, never more than one at a time. Do this "
    "before anything else. "
    "Ask for each field only once. Never re-ask for a field you already "
    "have, never ask the user to confirm or reformat it, and never judge "
    "whether an age or email 'looks' valid or complete -- that is not "
    "your job. "
    "You only ever see partially masked placeholders in place of real "
    "names and emails, e.g. 'P****' or 'p****@g*****.com' -- never real "
    "PII. "
    "As soon as you have all three, immediately call the "
    "check_eligibility tool exactly once with the age and email values "
    "(masked or not) -- it is the sole source of truth for eligibility, "
    "including whether the email counts as valid. Do not validate or "
    "second-guess the inputs yourself first. "
    "After the tool responds, tell the user the result plainly (eligible "
    "or not, and why), and restate the name, age, and email you used so "
    "they can see exactly what was evaluated -- when restating name or "
    "email, reuse the exact masked form you were given, don't rewrite or "
    "reformat it. "
    "Use the conversation history to remember details the user already "
    "gave you earlier -- don't ask again for information you already have."
)


class EligibilityChatbot:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        settings = get_settings()
        self.client = OpenAI(
            api_key=api_key or settings.api_key,
            base_url=base_url or settings.base_url,
            # OpenRouter-specific, optional headers: they show up in
            # OpenRouter's dashboard/rankings for your app. Harmless no-ops
            # against a plain OpenAI endpoint if you ever swap providers.
            default_headers={
                "HTTP-Referer": settings.app_url,
                "X-Title": settings.app_name,
            },
        )
        self.model = model or settings.model
        self.memory = SessionMemory(system_prompt=SYSTEM_PROMPT)

    def reset(self, user_id: str) -> None:
        self.memory.reset(user_id)

    def run(
        self,
        user_id: str,
        name: Optional[str] = None,
        age: Optional[int] = None,
        email: Optional[str] = None,
        message: Optional[str] = None,
        verbose: bool = True,
    ) -> str:
        """One turn of conversation for `user_id`. Pass name/age/email the
        first time they're shared; on later turns pass just `message` and
        the model will use what's already in memory."""
        session = self.memory.get(user_id)
        masker = session["masker"]
        messages: List[dict] = session["messages"]

        parts = []
        if name is not None:
            parts.append(f"Name: {name}")
        if age is not None:
            parts.append(f"Age: {age}")
        if email is not None:
            parts.append(f"Email: {email}")
        if parts:
            parts.append("Please check this user's eligibility.")
        if message:
            parts.append(message)
        raw_text = ", ".join(parts) if parts else (message or "")

        # --- Step 1: mask PII BEFORE anything is sent to the model --------
        # A blank raw_text means this is a fresh session with nothing said
        # yet -- skip adding a user turn so the model opens the conversation
        # (per SYSTEM_PROMPT) instead of replying to an empty message.
        if raw_text:
            masked_text = masker.mask(raw_text)
            masking_log.record(
                user_id=user_id,
                action="mask",
                context="user_message",
                before=raw_text,
                after=masked_text,
            )
            if verbose:
                print(f"[user_id] {user_id}")
                print(f"[raw]    {raw_text}")
                print(f"[masked] {masked_text}")
                print(f"[mapping so far] {masker.mapping}\n")

            messages.append({"role": "user", "content": masked_text})

        # --- Step 2: let the model decide whether to call the tool --------
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=[ELIGIBILITY_TOOL],
            tool_choice="auto",
        )

        choice = response.choices[0]
        messages.append(choice.message)

        if choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                if tool_call.function.name != "check_eligibility":
                    continue

                args = json.loads(tool_call.function.arguments)
                if verbose:
                    print(f"[tool_call args from model] {args}")

                # --- Step 3: de-anonymize ONLY inside trusted server code --
                real_age = int(args["age"])
                masked_email = str(args["email"])
                real_email = masker.unmask(masked_email)
                masking_log.record(
                    user_id=user_id,
                    action="unmask",
                    context="tool_call_email",
                    before=masked_email,
                    after=real_email,
                )

                result = check_eligibility(age=real_age, email=real_email)
                if verbose:
                    print(f"[real eligibility result] {result}\n")

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result),
                    }
                )

            # --- Step 4: let the model turn the tool result into prose ----
            final = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            final_message = final.choices[0].message
            messages.append(final_message)
            # --- Step 5: unmask ONLY the copy shown to the user; history --
            # sent back to the model on future turns stays masked.
            masked_reply = final_message.content or ""
            unmasked_reply = masker.unmask(masked_reply)
            masking_log.record(
                user_id=user_id,
                action="unmask",
                context="final_reply",
                before=masked_reply,
                after=unmasked_reply,
            )
            return unmasked_reply

        masked_reply = choice.message.content or ""
        unmasked_reply = masker.unmask(masked_reply)
        masking_log.record(
            user_id=user_id,
            action="unmask",
            context="final_reply",
            before=masked_reply,
            after=unmasked_reply,
        )
        return unmasked_reply