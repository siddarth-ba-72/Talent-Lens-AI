package com.talentlens.dto.request;

import com.talentlens.model.Role;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class GoogleCompleteSignupRequest {

    @NotBlank
    private String signupTicket;

    @NotNull
    private Role role;
}
