package com.talentlens.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;

@Document(collection = "sourcing_tasks")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SourcingTask {

    @Id
    private String id;

    private String searchId;
    private String runId;
    private List<String> platforms;
    private TaskStatus status;
    private int candidatesFound;
    private String error;
    private Instant startedAt;
    private Instant completedAt;
}
