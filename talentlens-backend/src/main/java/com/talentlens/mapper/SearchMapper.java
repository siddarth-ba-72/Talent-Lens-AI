package com.talentlens.mapper;

import com.talentlens.dto.response.ParsedJdDto;
import com.talentlens.dto.response.SearchResponse;
import com.talentlens.dto.response.SearchSummaryResponse;
import com.talentlens.model.Search;
import com.talentlens.model.embedded.ParsedJd;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(componentModel = "spring")
public interface SearchMapper {

    @Mapping(target = "sourcingStatus", expression = "java(search.getSourcingStatus().name())")
    SearchResponse toResponse(Search search);

    @Mapping(target = "sourcingStatus", expression = "java(search.getSourcingStatus().name())")
    SearchSummaryResponse toSummary(Search search);

    ParsedJdDto toParsedJdDto(ParsedJd parsedJd);
}
