package com.talentlens.config;

import com.talentlens.model.Candidate;
import com.talentlens.model.Search;
import com.talentlens.model.SourcingTask;
import com.talentlens.model.User;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.bson.Document;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.event.EventListener;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.index.CompoundIndexDefinition;
import org.springframework.data.mongodb.core.index.Index;
import org.springframework.data.mongodb.core.index.IndexOperations;

@Configuration
@RequiredArgsConstructor
@Slf4j
public class MongoConfig {

    private final MongoTemplate mongoTemplate;

    @EventListener(ApplicationReadyEvent.class)
    public void initIndexes() {
        log.info("Ensuring MongoDB indexes");

        idx(User.class).createIndex(new Index("email", Sort.Direction.ASC).unique());

        idx(Search.class).createIndex(new Index("userId", Sort.Direction.ASC));
        idx(Search.class).createIndex(new CompoundIndexDefinition(
                new Document("userId", 1).append("createdAt", -1)));
        idx(Search.class).createIndex(new Index("sharedWith", Sort.Direction.ASC));

        idx(Candidate.class).createIndex(new CompoundIndexDefinition(
                new Document("searchId", 1).append("runId", 1)
                        .append("source", 1).append("sourceUsername", 1)).unique());
        idx(Candidate.class).createIndex(new CompoundIndexDefinition(
                new Document("searchId", 1).append("isActive", 1).append("matchScore", -1)));

        idx(SourcingTask.class).createIndex(new Index("searchId", Sort.Direction.ASC));
        idx(SourcingTask.class).createIndex(new Index("status", Sort.Direction.ASC));

        log.info("MongoDB indexes created");
    }

    private IndexOperations idx(Class<?> entityClass) {
        return mongoTemplate.indexOps(entityClass);
    }
}
