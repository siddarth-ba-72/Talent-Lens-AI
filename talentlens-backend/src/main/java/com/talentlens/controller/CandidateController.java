package com.talentlens.controller;

import com.talentlens.dto.response.CandidateResponse;
import com.talentlens.dto.response.PageResponse;
import com.talentlens.exception.InvalidFileException;
import com.talentlens.repository.CandidateFilterParams;
import com.talentlens.service.CandidateService;
import com.talentlens.service.ExportServiceFactory;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/searches/{searchId}/candidates")
@RequiredArgsConstructor
public class CandidateController {

    private final CandidateService candidateService;
    private final ExportServiceFactory exportServiceFactory;

    @GetMapping
    public ResponseEntity<PageResponse<CandidateResponse>> listCandidates(
            @AuthenticationPrincipal String userId,
            @PathVariable String searchId,
            @RequestParam(required = false) List<String> skill,
            @RequestParam(required = false) String source,
            @RequestParam(required = false) Integer minScore,
            @RequestParam(required = false) Integer maxScore,
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "matchScore") String sortBy,
            @RequestParam(defaultValue = "desc") String sortOrder,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        CandidateFilterParams params = CandidateFilterParams.builder()
                .skills(skill)
                .source(source)
                .minScore(minScore)
                .maxScore(maxScore)
                .keyword(keyword)
                .build();

        Sort sort = Sort.by("desc".equalsIgnoreCase(sortOrder)
                ? Sort.Direction.DESC : Sort.Direction.ASC, sortBy);
        Pageable pageable = PageRequest.of(page, size, sort);

        return ResponseEntity.ok(candidateService.listCandidates(userId, searchId, params, pageable));
    }

    @DeleteMapping("/{candidateId}")
    public ResponseEntity<Void> softDelete(
            @AuthenticationPrincipal String userId,
            @PathVariable String searchId,
            @PathVariable String candidateId) {
        candidateService.softDelete(userId, searchId, candidateId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/export")
    public void export(
            @AuthenticationPrincipal String userId,
            @PathVariable String searchId,
            @RequestParam String format,
            @RequestParam(required = false) List<String> skill,
            @RequestParam(required = false) String source,
            @RequestParam(required = false) Integer minScore,
            @RequestParam(required = false) Integer maxScore,
            @RequestParam(required = false) String keyword,
            HttpServletResponse response) {

        if (format == null || format.isBlank()) {
            throw new InvalidFileException("Export format is required (csv or json)");
        }

        CandidateFilterParams params = CandidateFilterParams.builder()
                .skills(skill)
                .source(source)
                .minScore(minScore)
                .maxScore(maxScore)
                .keyword(keyword)
                .build();

        exportServiceFactory.get(format).export(searchId, params, response);
    }
}
