from app.models import Quote, Run


class RunResponse(Run):
    """A run as the API returns it. The quote is the public `Quote`, so its token and idempotency key
    (which the stored run keeps) never reach the browser."""

    quote: Quote | None = None
