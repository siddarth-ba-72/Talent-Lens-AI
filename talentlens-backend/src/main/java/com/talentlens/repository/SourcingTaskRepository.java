package com.talentlens.repository;

import com.talentlens.model.SourcingTask;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;

public interface SourcingTaskRepository extends MongoRepository<SourcingTask, String> {
    Optional<SourcingTask> findTopBySearchIdOrderByStartedAtDesc(String searchId);
    void deleteBySearchId(String searchId);
}
