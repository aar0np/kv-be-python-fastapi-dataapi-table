import React, { useState, FormEvent } from "react";
import VideoCard from "./VideoCard";

export interface VideoSummary {
  videoId: string;
  title: string;
  thumbnailUrl?: string | null;
  userId: string;
  submittedAt: string;
  content_rating?: string | null;
  category?: string | null;
  views: number;
  averageRating?: number | null;
}

interface Pagination {
  currentPage: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

interface PaginatedResponse {
  data: VideoSummary[];
  pagination: Pagination;
}

interface SemanticSearchBarProps {
  /**
   * Optional base URL for the API. Defaults to relative path
   * so that the component works when the front-end and backend
   * are served from the same origin (e.g. behind a reverse proxy).
   */
  apiBaseUrl?: string;
  /**
   * Number of results to request per page (default: 10)
   */
  pageSize?: number;
}

const SemanticSearchBar: React.FC<SemanticSearchBarProps> = ({
  apiBaseUrl = "",
  pageSize = 10,
}) => {
  const [query, setQuery] = useState<string>("");
  const [results, setResults] = useState<VideoSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      return;
    }
    await performSearch(query.trim());
  };

  const performSearch = async (q: string) => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      params.set("query", q);
      params.set("mode", "semantic");
      params.set("page", "1");
      params.set("pageSize", pageSize.toString());

      const response = await fetch(
        `${apiBaseUrl}/api/v1/search/videos?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error(`Backend search failed: ${response.status}`);
      }

      const payload: PaginatedResponse = await response.json();
      setResults(payload.data);
    } catch (err: any) {
      console.error(err);
      setError(err.message ?? "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="semantic-search-bar">
      <form onSubmit={handleSubmit} className="search-form">
        <input
          type="text"
          placeholder="Search videos…"
          aria-label="Search videos"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !query.trim()}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      <div className="results">
        {results.map((video) => (
          <VideoCard key={video.videoId} video={video} />
        ))}
      </div>
    </div>
  );
};

export default SemanticSearchBar; 