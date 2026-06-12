package com.talentlens.exception;

public class OidcException extends RuntimeException {
    private final String code;

    public OidcException(String code, String message) {
        super(message);
        this.code = code;
    }

    public OidcException(String code, String message, Throwable cause) {
        super(message, cause);
        this.code = code;
    }

    public String getCode() {
        return code;
    }
}
