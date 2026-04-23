package com.talentlens.dto.validation;

import com.talentlens.dto.request.CreateShareRequestRequest;
import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;
import org.springframework.util.StringUtils;

import java.util.regex.Pattern;

public class ShareRequestInputValidator implements ConstraintValidator<ValidShareRequestInput, CreateShareRequestRequest> {

    private static final Pattern OBJECT_ID_PATTERN = Pattern.compile("^[a-fA-F0-9]{24}$");

    @Override
    public boolean isValid(CreateShareRequestRequest value, ConstraintValidatorContext context) {
        if (value == null) {
            return true;
        }

        boolean valid = true;
        context.disableDefaultConstraintViolation();

        if (StringUtils.hasText(value.getSearchId()) && !OBJECT_ID_PATTERN.matcher(value.getSearchId()).matches()) {
            context.buildConstraintViolationWithTemplate("searchId must be a valid Mongo ObjectId")
                    .addPropertyNode("searchId")
                    .addConstraintViolation();
            valid = false;
        }

        if (StringUtils.hasText(value.getRecruiterUserId()) && !OBJECT_ID_PATTERN.matcher(value.getRecruiterUserId()).matches()) {
            context.buildConstraintViolationWithTemplate("recruiterUserId must be a valid Mongo ObjectId")
                    .addPropertyNode("recruiterUserId")
                    .addConstraintViolation();
            valid = false;
        }

        if (StringUtils.hasText(value.getSearchId())
                && StringUtils.hasText(value.getRecruiterUserId())
                && value.getSearchId().equals(value.getRecruiterUserId())) {
            context.buildConstraintViolationWithTemplate("searchId and recruiterUserId cannot be the same value")
                    .addConstraintViolation();
            valid = false;
        }

        return valid;
    }
}
