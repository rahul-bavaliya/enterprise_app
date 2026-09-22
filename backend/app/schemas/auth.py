from sqlmodel import Field, SQLModel


class Message(SQLModel):
    message: str = Field(
        description="Human-readable status or success message.",
        schema_extra={"example": "User deleted successfully"},
    )


class Token(SQLModel):
    access_token: str = Field(
        description="JWT access token used for authenticated API requests.",
        schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )
    token_type: str = Field(
        default="bearer",
        description="Type of token returned by the authentication endpoint.",
        schema_extra={"example": "bearer"},
    )


class TokenPayload(SQLModel):
    sub: str | None = Field(
        default=None,
        description="Subject claim representing the user identifier in the JWT.",
        schema_extra={"example": "6a5d5a7e-4f8d-4b2a-9bd7-2e8a3f1c5b8a"},
    )


class NewPassword(SQLModel):
    token: str = Field(
        description="Password reset token used to authorize a new password.",
        schema_extra={"example": "eyJzdWIiOiJ..."},
    )
    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="New password to be stored after the reset token is validated.",
        schema_extra={"example": "ResetPass!456"},
    )
