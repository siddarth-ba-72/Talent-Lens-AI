package com.talentlens.mapper;

import com.talentlens.dto.response.ShareRequestResponse;
import com.talentlens.model.ShareRequest;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(componentModel = "spring")
public interface ShareRequestMapper {

    @Mapping(target = "status", expression = "java(shareRequest.getStatus().name())")
    ShareRequestResponse toResponse(ShareRequest shareRequest);
}