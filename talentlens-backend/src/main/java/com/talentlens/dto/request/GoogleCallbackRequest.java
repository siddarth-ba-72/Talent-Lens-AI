package com.talentlens.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class GoogleCallbackRequest {

    @NotBlank
    private String code;

    @NotBlank
    private String codeVerifier;

    @NotBlank
    private String nonce;
}
