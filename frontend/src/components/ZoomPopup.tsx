import { Star } from 'lucide-react';
import { getViewerImageUrl } from '../api/client';
import type { ViewerItem } from '../api/types';

interface ZoomPopupProps {
  item: ViewerItem;
  channelNames: string[];
  mouseX: number;
  mouseY: number;
  cacheKey: number;
}

export function ZoomPopup({
  item,
  channelNames,
  mouseX,
  mouseY,
  cacheKey,
}: ZoomPopupProps) {
  const channelCount = Math.max(1, item.n_channels);
  const popupWidth = Math.min(channelCount * 168 + 32, window.innerWidth - 32);
  const popupHeight = 258;
  const gap = 18;

  let left = mouseX + gap;
  let top = mouseY + gap;
  if (left + popupWidth > window.innerWidth - gap) {
    left = mouseX - popupWidth - gap;
  }
  if (top + popupHeight > window.innerHeight - gap) {
    top = mouseY - popupHeight - gap;
  }
  left = Math.max(gap, left);
  top = Math.max(gap, top);

  return (
    <div className="zoom-popup" style={{ left, top, width: popupWidth }}>
      <div className="zoom-popup__header">
        <span className="zoom-popup__filename">{item.filename}</span>
        {item.is_favorite && <Star size={14} fill="currentColor" />}
      </div>
      <div className="zoom-popup__channels">
        {Array.from({ length: channelCount }).map((_, index) => (
          <div className="zoom-popup__channel" key={index}>
            <div className="zoom-popup__label">
              {channelNames[index] || `Channel ${index + 1}`}
            </div>
            <div className="zoom-popup__frame">
              <img
                src={getViewerImageUrl(item.id, index, {
                  normalize: false,
                  cacheKey,
                })}
                alt={channelNames[index] || `Channel ${index + 1}`}
                draggable={false}
              />
            </div>
          </div>
        ))}
      </div>
      <div className="zoom-popup__footer">
        <span>{item.shape.length ? item.shape.join(' x ') : 'unknown shape'}</span>
        <span>{channelCount} channels</span>
      </div>
    </div>
  );
}
