package com.talentlens.repository;

import com.talentlens.model.Candidate;
import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;

public interface CandidateRepository extends MongoRepository<Candidate, String>, CandidateRepositoryCustom {
    Optional<Candidate> findByIdAndSearchId(String id, String searchId);
    void deleteBySearchId(String searchId);
}
