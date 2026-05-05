class PricingDomainException(Exception):
    """Base exception for the pricing domain."""
    pass


class MaterialNotFoundException(PricingDomainException):
    """Raised when a material is not found in the catalog."""
    def __init__(self, material_id: int):
        self.material_id = material_id
        super().__init__(f"Material with ID {material_id} not found.")


class InsufficientDataException(PricingDomainException):
    """Raised when there isn't enough historical data to generate a forecast."""
    def __init__(self, message: str):
        super().__init__(message)


class ExternalRegressorError(PricingDomainException):
    """Raised when there are issues with external regressors (missing data, alignment, etc.)."""
    def __init__(self, message: str):
        super().__init__(message)


class ExternalIndexSyncError(PricingDomainException):
    """Raised when an external index cannot be fetched or persisted."""

    def __init__(self, message: str):
        super().__init__(message)


class PriceImputationError(PricingDomainException):
    """Raised when missing prices cannot be imputed safely."""

    def __init__(self, message: str):
        super().__init__(message)
