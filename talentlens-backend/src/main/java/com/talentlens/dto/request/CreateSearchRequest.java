package com.talentlens.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateSearchRequest {

    @NotBlank(message = "jdText must not be blank")
    private String jdText;
}
