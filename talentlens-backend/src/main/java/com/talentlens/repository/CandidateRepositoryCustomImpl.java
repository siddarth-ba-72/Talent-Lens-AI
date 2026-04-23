package com.talentlens.repository;

import com.talentlens.model.Candidate;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.List;

public class CandidateRepositoryCustomImpl implements CandidateRepositoryCustom {

    private final MongoTemplate mongoTemplate;

    public CandidateRepositoryCustomImpl(MongoTemplate mongoTemplate) {
        this.mongoTemplate = mongoTemplate;
    }

    @Override
    public Page<Candidate> findWithFilters(String searchId, CandidateFilterParams params, Pageable pageable) {
        Criteria criteria = buildCriteria(searchId, params);
        Query query = new Query(criteria).with(pageable);
        Query countQuery = new Query(criteria);

        List<Candidate> results = mongoTemplate.find(query, Candidate.class);
        long total = mongoTemplate.count(countQuery, Candidate.class);

        return new PageImpl<>(results, pageable, total);
    }

    @Override
    public List<Candidate> findAllWithFilters(String searchId, CandidateFilterParams params) {
        Criteria criteria = buildCriteria(searchId, params);
        return mongoTemplate.find(new Query(criteria), Candidate.class);
    }

    private Criteria buildCriteria(String searchId, CandidateFilterParams params) {
        List<Criteria> criteriaList = new ArrayList<>();

        criteriaList.add(Criteria.where("searchId").is(searchId));
        criteriaList.add(Criteria.where("isActive").is(true));

        if (!CollectionUtils.isEmpty(params.getSkills())) {
            criteriaList.add(Criteria.where("skills").in(params.getSkills()));
        }

        if (StringUtils.hasText(params.getSource())) {
            criteriaList.add(Criteria.where("source").is(params.getSource()));
        }

        if (params.getMinScore() != null) {
            criteriaList.add(Criteria.where("matchScore").gte(params.getMinScore()));
        }

        if (params.getMaxScore() != null) {
            criteriaList.add(Criteria.where("matchScore").lte(params.getMaxScore()));
        }

        if (StringUtils.hasText(params.getKeyword())) {
            Criteria keywordCriteria = new Criteria().orOperator(
                    Criteria.where("name").regex(params.getKeyword(), "i"),
                    Criteria.where("bio").regex(params.getKeyword(), "i"),
                    Criteria.where("sourceUsername").regex(params.getKeyword(), "i")
            );
            criteriaList.add(keywordCriteria);
        }

        return new Criteria().andOperator(criteriaList.toArray(new Criteria[0]));
    }
}
