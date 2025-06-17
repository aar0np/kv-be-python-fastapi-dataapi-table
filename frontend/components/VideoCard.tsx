import React from "react";
import { VideoSummary } from "./SemanticSearchBar";

interface VideoCardProps {
  video: VideoSummary;
}

const VideoCard: React.FC<VideoCardProps> = ({ video }) => {
  return (
    <div className="video-card">
      {video.thumbnailUrl && (
        // eslint-disable-next-line @next/next/no-img-element -- plain img is fine here
        <img
          src={video.thumbnailUrl}
          alt={video.title}
          className="thumbnail"
        />
      )}
      <h3>{video.title}</h3>
    </div>
  );
};

export default VideoCard; 