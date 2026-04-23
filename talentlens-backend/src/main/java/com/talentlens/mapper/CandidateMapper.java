package com.talentlens.mapper;

import com.talentlens.dto.response.CandidateResponse;
import com.talentlens.dto.response.ScoreBreakdownDto;
import com.talentlens.model.Candidate;
import com.talentlens.model.embedded.ScoreBreakdown;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(componentModel = "spring")
public interface CandidateMapper {

    @Mapping(target = "source", expression = "java(candidate.getSource().name())")
    CandidateResponse toResponse(Candidate candidate);

    ScoreBreakdownDto toScoreBreakdownDto(ScoreBreakdown scoreBreakdown);
}
