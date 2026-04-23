package com.talentlens.service.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.talentlens.exception.ResourceNotFoundException;
import com.talentlens.mapper.CandidateMapper;
import com.talentlens.model.Candidate;
import com.talentlens.repository.CandidateFilterParams;
import com.talentlens.repository.CandidateRepository;
import com.talentlens.repository.SearchRepository;
import com.talentlens.service.ExportService;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.List;

@Service("json")
@RequiredArgsConstructor
@Slf4j
public class JsonExportService implements ExportService {

    private final CandidateRepository candidateRepository;
    private final SearchRepository searchRepository;
    private final CandidateMapper candidateMapper;

    private final ObjectMapper objectMapper = new ObjectMapper()
            .registerModule(new JavaTimeModule())
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

    @Override
    public String format() {
        return "json";
    }

    @Override
    public void export(String searchId, CandidateFilterParams params, HttpServletResponse response) {
        if (!searchRepository.existsById(searchId)) {
            throw new ResourceNotFoundException("Search not found: " + searchId);
        }

        List<Candidate> candidates = candidateRepository.findAllWithFilters(searchId, params);

        response.setContentType("application/json");
        response.setHeader("Content-Disposition", "attachment; filename=\"candidates-" + searchId + ".json\"");

        try {
            objectMapper.writeValue(
                    response.getOutputStream(),
                    candidates.stream().map(candidateMapper::toResponse).toList()
            );
        } catch (IOException ex) {
            log.error("Error writing JSON export for searchId={}", searchId, ex);
        }
    }
}
