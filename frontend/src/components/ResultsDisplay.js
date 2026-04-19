import React, { useState } from 'react';
import './ResultsDisplay.css';

function ResultsDisplay({ result, onContinue }) {
  const [expandedMatch, setExpandedMatch] = useState(null);

  if (result.type === 'register') {
    return (
      <div className="results-container">
        <div className="success-icon">✓</div>
        <h2>Media Registered Successfully</h2>
        <p className="message">{result.message}</p>

        <div className="result-details">
          <div className="detail-row">
            <label>Filename:</label>
            <span className="detail-value">{result.data.filename}</span>
          </div>
          <div className="detail-row">
            <label>Asset ID:</label>
            <span className="detail-value mono">{result.data.asset_id}</span>
          </div>
          <div className="detail-row">
            <label>SHA-256 Hash:</label>
            <span className="detail-value mono hash">{result.data.sha256}</span>
          </div>
          <div className="detail-row">
            <label>Registered:</label>
            <span className="detail-value">
              {new Date(result.data.created_at).toLocaleString()}
            </span>
          </div>
        </div>

        <button className="continue-button" onClick={onContinue}>
          Register Another Media
        </button>
      </div>
    );
  }

  // Check Provenance Results
  const topMatch = result.data.top_match;
  const allMatches = result.data.all_matches || [];
  const totalMatches = result.data.total_matches;

  const getTierColor = (tier) => {
    switch (tier) {
      case 'tier1':
        return '#c53030'; // Red
      case 'tier2':
        return '#dd6b20'; // Orange
      case 'tier3':
        return '#f6ad55'; // Light Orange
      case 'tier4':
        return '#a0aec0'; // Gray
      default:
        return '#718096';
    }
  };

  const getTierLabel = (tier) => {
    switch (tier) {
      case 'tier1':
        return 'EXACT MATCH';
      case 'tier2':
        return 'VERY SIMILAR';
      case 'tier3':
        return 'SIMILAR';
      case 'tier4':
        return 'POSSIBLY RELATED';
      default:
        return 'UNKNOWN';
    }
  };

  return (
    <div className="results-container">
      {topMatch ? (
        <>
          <div className="top-match-section">
            <h2>Top Match Found</h2>

            <div className="image-comparison">
              <div className="query-image-container">
                <h3>Your Image</h3>
                {result.queryImageBase64 && (
                  <img
                    src={`data:image/jpeg;base64,${result.queryImageBase64}`}
                    alt="Query"
                    className="comparison-image"
                    onError={(e) => {
                      e.target.src =
                        'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23ddd" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" font-size="14" fill="%23999" text-anchor="middle" dy=".3em"%3EImage unavailable%3C/text%3E%3C/svg%3E';
                    }}
                  />
                )}
              </div>

              <div className="match-image-container">
                <h3>Best Match</h3>
                {topMatch.image_base64 && (
                  <img
                    src={`data:image/jpeg;base64,${topMatch.image_base64}`}
                    alt="Match"
                    className="comparison-image"
                    onError={(e) => {
                      e.target.src =
                        'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23ddd" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" font-size="14" fill="%23999" text-anchor="middle" dy=".3em"%3EImage unavailable%3C/text%3E%3C/svg%3E';
                    }}
                  />
                )}
              </div>
            </div>

            <div className="confidence-badge" style={{ borderLeft: `4px solid ${getTierColor(topMatch.confidence_tier)}` }}>
              <div className="confidence-tier" style={{ color: getTierColor(topMatch.confidence_tier) }}>
                {getTierLabel(topMatch.confidence_tier)}
              </div>
              <div className="similarity-score">
                <span className="score">{topMatch.similarity_score.toFixed(1)}%</span>
                <span className="score-label">Similarity</span>
              </div>
            </div>

            <div className="match-details">
              <div className="detail-row">
                <label>Creator ID:</label>
                <span>{topMatch.creator_id}</span>
              </div>
              <div className="detail-row">
                <label>Registered:</label>
                <span>
                  {topMatch.created_at
                    ? new Date(topMatch.created_at).toLocaleString()
                    : 'Unknown'}
                </span>
              </div>

              <div className="action-buttons">
                <button className="report-button" onClick={() => alert('Report submitted')}>
                  Report Media
                </button>
              </div>
            </div>
          </div>

          {allMatches.length > 0 && (
            <div className="all-matches-section">
              <h3>All Matches ({totalMatches} total)</h3>
              <p className="matches-info">Showing top {Math.min(20, allMatches.length)} matches</p>

              <div className="matches-list">
                {allMatches.map((match, index) => (
                  <div key={index} className="match-item">
                    <button
                      className="match-header"
                      onClick={() =>
                        setExpandedMatch(expandedMatch === index ? null : index)
                      }
                    >
                      <div className="match-rank">#{index + 1}</div>
                      <div className="match-summary">
                        <div className="score-summary">
                          {match.similarity_score.toFixed(1)}%
                        </div>
                      </div>
                      <div className="expand-icon">
                        {expandedMatch === index ? '−' : '+'}
                      </div>
                    </button>

                    {expandedMatch === index && (
                      <div className="match-expanded">
                        {match.image_base64 && (
                          <div className="expanded-match-image">
                            <img
                              src={`data:image/jpeg;base64,${match.image_base64}`}
                              alt={match.filename}
                              onError={(e) => {
                                e.target.src =
                                  'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="150" height="150"%3E%3Crect fill="%23ddd" width="150" height="150"/%3E%3Ctext x="50%25" y="50%25" font-size="12" fill="%23999" text-anchor="middle" dy=".3em"%3EImage unavailable%3C/text%3E%3C/svg%3E';
                              }}
                            />
                          </div>
                        )}
                        <div className="detail-row">
                          <label>Creator:</label>
                          <span>{match.creator_id}</span>
                        </div>
                        <div className="detail-row">
                          <label>Tier:</label>
                          <span
                            style={{
                              color: getTierColor(match.confidence_tier),
                              fontWeight: 600,
                            }}
                          >
                            {getTierLabel(match.confidence_tier)}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="no-results">
          <div className="no-results-icon">X</div>
          <h2>No Matches Found</h2>
          <p>This image is not in our database</p>
        </div>
      )}

      <button className="continue-button" onClick={onContinue}>
        Check Another Image
      </button>
    </div>
  );
}

export default ResultsDisplay;
