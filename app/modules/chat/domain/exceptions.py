class CommercialAssistantError(Exception):
    """Base error for commercial request interpretation and proposal generation."""


class InvalidCommercialRequest(CommercialAssistantError):
    """The interpreted or confirmed commercial request is invalid."""


class CommercialInterpretationError(CommercialAssistantError):
    """The conversational provider returned an unusable structured response."""
