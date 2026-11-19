class AppError(Exception):
    """Base class for errors that are shown to the user.

    `message` is plain language and safe to return to the client. Technical detail
    (raw CLI output, validation errors, stack traces) goes to the logs only.
    """

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class RunNotFoundError(AppError):
    status_code = 404
    code = "run_not_found"

    def __init__(self, run_id: str) -> None:
        super().__init__("We couldn't find that session. Please start again.")
        self.run_id = run_id


class InvalidRunStateError(AppError):
    status_code = 409
    code = "invalid_run_state"

    def __init__(self) -> None:
        super().__init__("That step isn't available yet. Please follow the steps in order.")


class DomainNotAvailableError(AppError):
    status_code = 422
    code = "domain_not_available"

    def __init__(self) -> None:
        super().__init__("That domain isn't in the list of available domains. Please pick one from the list.")


class DomainTakenError(AppError):
    status_code = 409
    code = "domain_taken"

    def __init__(self) -> None:
        super().__init__("Sorry, that domain was just taken. Please pick another one.")


class ConfirmationMismatchError(AppError):
    status_code = 409
    code = "confirmation_mismatch"

    def __init__(self) -> None:
        super().__init__("The domain or price changed. Please review it again.")


class QuoteExpiredError(AppError):
    status_code = 409
    code = "quote_expired"

    def __init__(self) -> None:
        super().__init__("The price is no longer locked. Please review the current price and try again.")


class PurchaseFailedError(AppError):
    status_code = 502
    code = "purchase_failed"

    def __init__(self) -> None:
        super().__init__("We couldn't register that domain. Please try again.")


class RegenerationLimitError(AppError):
    status_code = 409
    code = "regeneration_limit"

    def __init__(self, cap: int) -> None:
        super().__init__(f"You can regenerate the site up to {cap} times. Please keep one of the versions.")


class ClaudeError(AppError):
    status_code = 502
    code = "generation_failed"

    def __init__(self) -> None:
        super().__init__("We couldn't generate that just now. Please try again.")


class GddyError(AppError):
    status_code = 502
    code = "domain_service_failed"

    def __init__(self) -> None:
        super().__init__("We couldn't reach the domain service just now. Please try again.")


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"

    def __init__(self, message: str = "You've sent a few messages already. Please try again a little later.") -> None:
        super().__init__(message)


class MailError(AppError):
    status_code = 502
    code = "mail_failed"

    def __init__(self) -> None:
        super().__init__("We couldn't send your message just now. Please try again in a moment.")


class MailNotConfiguredError(AppError):
    status_code = 503
    code = "mail_not_configured"

    def __init__(self) -> None:
        super().__init__("Our contact form isn't available right now. Please try again later.")
