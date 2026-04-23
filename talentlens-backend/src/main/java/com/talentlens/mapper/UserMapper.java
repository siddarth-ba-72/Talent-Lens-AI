package com.talentlens.mapper;

import com.talentlens.dto.response.RecruiterResponse;
import com.talentlens.dto.response.UserResponse;
import com.talentlens.model.User;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(componentModel = "spring")
public interface UserMapper {

    @Mapping(target = "role", expression = "java(user.getRole().name())")
    UserResponse toResponse(User user);

    RecruiterResponse toRecruiterResponse(User user);
}