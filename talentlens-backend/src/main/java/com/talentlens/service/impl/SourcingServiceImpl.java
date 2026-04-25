package com.talentlens.service.impl;

import com.talentlens.dto.ai.SourcingRequestPayload;
import com.talentlens.dto.request.SourcingRequest;
import com.talentlens.dto.response.SourcingStatusResponse;
import com.talentlens.exception.ForbiddenException;
import com.talentlens.exception.InvalidFileException;
import com.talentlens.exception.ResourceNotFoundException;
import com.talentlens.model.Search;
import com.talentlens.model.SourcingStatus;
import com.talentlens.model.SourcingTask;
import com.talentlens.model.TaskStatus;
import com.talentlens.repository.SearchRepository;
import com.talentlens.repository.SourcingTaskRepository;
import com.talentlens.service.AsyncSourcingExecutor;
import com.talentlens.service.SourcingService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.Set;

@Service
@RequiredArgsConstructor
@Slf4j
public class SourcingServiceImpl implements SourcingService {

    private static final Set<String> ALLOWED_PLATFORMS = Set.of("GITHUB", "STACKOVERFLOW", "LEETCODE", "PEOPLES_DATA");
    private static final String ALLOWED_PLATFORMS_TEXT = "GITHUB, STACKOVERFLOW, LEETCODE, PEOPLES_DATA";
    private static final DateTimeFormatter RUN_ID_FORMATTER =
        DateTimeFormatter.ofPattern("'run_'yyyyMMdd'_'HHmmss'_'SSS").withZone(ZoneOffset.UTC);

    private final SearchRepository searchRepository;
    private final SourcingTaskRepository sourcingTaskRepository;
    private final AsyncSourcingExecutor asyncSourcingExecutor;

    @Override
    public SourcingStatusResponse triggerSourcing(String userId, String searchId, SourcingRequest request) {
        Search search = searchRepository.findById(searchId)
                .orElseThrow(() -> new ResourceNotFoundException("Search not found: " + searchId));

        if (!search.getUserId().equals(userId)) {
            throw new ForbiddenException("Access denied");
        }

        if (search.getSourcingStatus() == SourcingStatus.IN_PROGRESS) {
            throw new InvalidFileException("Sourcing is already in progress for this search");
        }

        validatePlatforms(request.getPlatforms());

        String runId = RUN_ID_FORMATTER.format(Instant.now());

        SourcingTask task = SourcingTask.builder()
                .searchId(searchId)
                .runId(runId)
                .platforms(request.getPlatforms())
                .status(TaskStatus.PENDING)
                .candidatesFound(0)
                .startedAt(Instant.now())
                .build();

        SourcingTask savedTask = sourcingTaskRepository.save(task);

        search.setSourcingStatus(SourcingStatus.IN_PROGRESS);
        search.setSourcingPlatforms(request.getPlatforms());
        search.setUpdatedAt(Instant.now());
        searchRepository.save(search);

        SourcingRequestPayload payload = SourcingRequestPayload.builder()
                .taskId(savedTask.getId())
                .searchId(searchId)
                .runId(runId)
                .parsedJd(search.getParsedJd())
                .platforms(request.getPlatforms())
                .timestamp(Instant.now())
                .build();

        asyncSourcingExecutor.execute(payload);

        return toStatusResponse(savedTask, searchId);
    }

    @Override
    public SourcingStatusResponse getStatus(String userId, String searchId) {
        searchRepository.findById(searchId)
                .orElseThrow(() -> new ResourceNotFoundException("Search not found: " + searchId));

        SourcingTask task = sourcingTaskRepository.findTopBySearchIdOrderByStartedAtDesc(searchId)
                .orElseThrow(() -> new ResourceNotFoundException("No sourcing task found for search: " + searchId));

        return toStatusResponse(task, searchId);
    }

    private void validatePlatforms(java.util.List<String> platforms) {
        platforms.forEach(p -> {
            if (!ALLOWED_PLATFORMS.contains(p)) {
                throw new InvalidFileException("Invalid platform: " + p + ". Allowed: " + ALLOWED_PLATFORMS_TEXT);
            }
        });
    }

    private SourcingStatusResponse toStatusResponse(SourcingTask task, String searchId) {
        return new SourcingStatusResponse(
                task.getId(),
                searchId,
                task.getRunId(),
                task.getStatus().name(),
                task.getCandidatesFound(),
                task.getError(),
                task.getStartedAt(),
                task.getCompletedAt()
        );
    }
}
