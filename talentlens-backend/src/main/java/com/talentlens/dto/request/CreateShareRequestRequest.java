package com.talentlens.dto.request;

import com.talentlens.dto.validation.ValidShareRequestInput;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
@ValidShareRequestInput
public class CreateShareRequestRequest {

    @NotBlank
    private String searchId;

    @NotBlank
    private String recruiterUserId;

    @Size(max = 500)
    private String note;
}