package com.talentlens.service.impl;

import com.talentlens.dto.ai.SourcedCandidatePayload;
import com.talentlens.dto.ai.SourcingRequestPayload;
import com.talentlens.dto.ai.SourcingResultPayload;
import com.talentlens.model.Candidate;
import com.talentlens.model.CandidateSource;
import com.talentlens.model.Search;
import com.talentlens.model.SourcingStatus;
import com.talentlens.model.SourcingTask;
import com.talentlens.model.TaskStatus;
import com.talentlens.model.embedded.ScoreBreakdown;
import com.talentlens.repository.CandidateRepository;
import com.talentlens.repository.SearchRepository;
import com.talentlens.repository.SourcingTaskRepository;
import com.talentlens.service.AiServiceClient;
import com.talentlens.service.AsyncSourcingExecutor;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

@Service
@RequiredArgsConstructor
@Slf4j
public class AsyncSourcingExecutorImpl implements AsyncSourcingExecutor {

    private static final int MAX_CANDIDATES_PER_RUN = 20;

    private final AiServiceClient aiServiceClient;
    private final SourcingTaskRepository sourcingTaskRepository;
    private final SearchRepository searchRepository;
    private final CandidateRepository candidateRepository;

    @Override
    @Async
    public void execute(SourcingRequestPayload payload) {
        log.info("Async sourcing started: searchId={}, taskId={}, platforms={}",
                payload.getSearchId(), payload.getTaskId(), payload.getPlatforms());
        try {
            SourcingResultPayload result = aiServiceClient.sourceCandidates(payload);
            processResult(result);
        } catch (Exception ex) {
            log.error("Sourcing failed for searchId={}, taskId={}: {}",
                    payload.getSearchId(), payload.getTaskId(), ex.getMessage(), ex);
            markFailed(payload.getTaskId(), payload.getSearchId(), ex.getMessage());
        }
    }

    private void processResult(SourcingResultPayload message) {
        SourcingTask task = sourcingTaskRepository.findById(message.getTaskId()).orElse(null);
        if (task == null) {
            log.warn("SourcingTask not found for taskId={}, skipping result processing", message.getTaskId());
            return;
        }

        TaskStatus newTaskStatus = "COMPLETED".equalsIgnoreCase(message.getStatus())
                ? TaskStatus.COMPLETED
                : TaskStatus.FAILED;

        List<SourcedCandidatePayload> candidateMessages = newTaskStatus == TaskStatus.COMPLETED
                ? sanitize(message)
                : List.of();

        if (newTaskStatus == TaskStatus.COMPLETED) {
            persistCandidates(message.getSearchId(), message.getRunId(), candidateMessages);
        }

        task.setStatus(newTaskStatus);
        task.setCandidatesFound(candidateMessages.size());
        task.setError(message.getError());
        task.setCompletedAt(message.getCompletedAt());
        sourcingTaskRepository.save(task);

        searchRepository.findById(message.getSearchId()).ifPresent(search -> {
            SourcingStatus newSourcingStatus = newTaskStatus == TaskStatus.COMPLETED
                    ? SourcingStatus.COMPLETED
                    : SourcingStatus.FAILED;
            search.setSourcingStatus(newSourcingStatus);
            if (newTaskStatus == TaskStatus.COMPLETED) {
                search.setCandidateCount(
                        (int) candidateRepository.countBySearchIdAndIsActiveTrue(search.getId()));
            }
            search.setUpdatedAt(Instant.now());
            searchRepository.save(search);
        });

        log.info("Sourcing result processed: searchId={}, status={}, candidatesFound={}",
                message.getSearchId(), message.getStatus(), candidateMessages.size());
    }

    private void markFailed(String taskId, String searchId, String error) {
        sourcingTaskRepository.findById(taskId).ifPresent(task -> {
            task.setStatus(TaskStatus.FAILED);
            task.setError(error);
            task.setCompletedAt(Instant.now());
            sourcingTaskRepository.save(task);
        });
        searchRepository.findById(searchId).ifPresent(search -> {
            search.setSourcingStatus(SourcingStatus.FAILED);
            search.setUpdatedAt(Instant.now());
            searchRepository.save(search);
        });
    }

    private List<SourcedCandidatePayload> sanitize(SourcingResultPayload message) {
        List<SourcedCandidatePayload> candidates = message.getCandidates();
        if (candidates == null || candidates.isEmpty()) {
            return List.of();
        }
        List<SourcedCandidatePayload> sanitized = candidates.stream()
                .filter(Objects::nonNull)
                .limit(MAX_CANDIDATES_PER_RUN)
                .toList();
        if (candidates.size() > MAX_CANDIDATES_PER_RUN) {
            log.warn("Received {} candidates for taskId={}, capping at {}",
                    candidates.size(), message.getTaskId(), MAX_CANDIDATES_PER_RUN);
        }
        return sanitized;
    }

    private void persistCandidates(String searchId, String rawRunId, List<SourcedCandidatePayload> candidateMessages) {
        if (candidateMessages.isEmpty()) {
            return;
        }
        String runId = StringUtils.hasText(rawRunId) ? rawRunId : "run_unknown";

        for (SourcedCandidatePayload cm : candidateMessages) {
            if (!StringUtils.hasText(cm.getProfileUrl()) || !StringUtils.hasText(cm.getSourceUsername())) {
                log.warn("Skipping invalid candidate for searchId={}, runId={}", searchId, runId);
                continue;
            }

            ScoreBreakdown scoreBreakdown = cm.getScoreBreakdown() != null
                    ? cm.getScoreBreakdown()
                    : ScoreBreakdown.builder()
                    .skillMatch(cm.getMatchScore())
                    .experienceMatch(cm.getMatchScore())
                    .overallFit(cm.getMatchScore())
                    .build();

            Candidate candidate = Candidate.builder()
                    .searchId(searchId)
                    .runId(runId)
                    .name(StringUtils.hasText(cm.getName()) ? cm.getName() : cm.getSourceUsername())
                    .email(cm.getEmail())
                    .avatarUrl(cm.getAvatarUrl())
                    .profileUrl(cm.getProfileUrl())
                    .source(resolveSource(cm.getSource()))
                    .sourceUsername(cm.getSourceUsername())
                    .skills(cm.getSkills() != null ? cm.getSkills() : List.of())
                    .bio(cm.getBio())
                    .location(cm.getLocation())
                    .experience(cm.getExperience())
                    .matchScore(cm.getMatchScore())
                    .scoreBreakdown(scoreBreakdown)
                    .isActive(true)
                    .sourcedAt(cm.getSourcedAt() != null ? cm.getSourcedAt() : Instant.now())
                    .createdAt(Instant.now())
                    .build();

            try {
                candidateRepository.save(candidate);
            } catch (DuplicateKeyException ex) {
                log.debug("Duplicate candidate skipped: searchId={}, runId={}, sourceUsername={}",
                        searchId, runId, cm.getSourceUsername());
            }
        }
    }

    private CandidateSource resolveSource(String source) {
        if (!StringUtils.hasText(source)) {
            return CandidateSource.OTHER;
        }
        try {
            return CandidateSource.valueOf(source.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ex) {
            return CandidateSource.OTHER;
        }
    }
}
