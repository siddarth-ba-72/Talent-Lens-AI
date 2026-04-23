package com.talentlens.dto.request;

import com.talentlens.model.Role;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class RegisterRequest {

    @NotBlank
    @Size(max = 100)
    private String name;

    @NotBlank
    @Email
    private String email;

    @NotBlank
    @Size(min = 8, max = 100)
    private String password;

    private Role role;

    @Min(1)
    @Max(2)
    private Integer roleIndex;

    @AssertTrue(message = "Either role or roleIndex must be provided")
    public boolean isRoleSelectionPresent() {
        return role != null || roleIndex != null;
    }

    public Role resolveRole() {
        if (role != null) {
            return role;
        }
        if (roleIndex == null) {
            throw new IllegalStateException("Either role or roleIndex must be provided");
        }
        return Role.fromIndex(roleIndex);
    }
}
