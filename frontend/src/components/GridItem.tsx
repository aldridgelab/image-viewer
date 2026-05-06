import { Star } from 'lucide-react';
import { getViewerCompositeUrl, getViewerImageUrl } from '../api/client';
import type { ViewerCompositeChannels, ViewerItem, ViewerRenderMode } from '../api/types';

interface GridItemProps {
  item: ViewerItem;
  channel: number;
  renderMode: ViewerRenderMode;
  compositeChannels: ViewerCompositeChannels;
  cacheKey: number;
  onOpen: (item: ViewerItem) => void;
  onFavoriteToggle: (item: ViewerItem) => void;
  onMouseEnter: (item: ViewerItem, event: React.MouseEvent) => void;
  onMouseLeave: () => void;
  onMouseMove: (event: React.MouseEvent) => void;
}

export function GridItem({
  item,
  channel,
  renderMode,
  compositeChannels,
  cacheKey,
  onOpen,
  onFavoriteToggle,
  onMouseEnter,
  onMouseLeave,
  onMouseMove,
}: GridItemProps) {
  const thumbnailChannel = item.n_channels > 0 ? Math.min(channel, item.n_channels - 1) : 0;
  const imageSrc =
    renderMode === 'composite'
      ? getViewerCompositeUrl(item.id, {
          channels: compositeChannels,
          channelCount: item.n_channels,
          normalize: false,
          cacheKey,
        })
      : getViewerImageUrl(item.id, thumbnailChannel, {
          normalize: false,
          cacheKey,
        });

  return (
    <button
      type="button"
      className={`image-card ${item.is_favorite ? 'is-favorite' : ''}`}
      onClick={() => onOpen(item)}
      onMouseEnter={(event) => onMouseEnter(item, event)}
      onMouseLeave={onMouseLeave}
      onMouseMove={onMouseMove}
      title={item.filename}
    >
      <span className="image-card__frame">
        <img
          src={imageSrc}
          alt={renderMode === 'composite' ? `${item.filename} RGB composite` : item.filename}
          loading="lazy"
          draggable={false}
        />
      </span>
      <span className="image-card__meta">
        <span className="image-card__name">{item.id}</span>
        <span className="image-card__detail">
          {item.n_channels} ch
          {renderMode === 'composite' ? ' · RGB' : ''}
          {item.axes ? ` · ${item.axes}` : ''}
        </span>
      </span>
      <span
        role="button"
        tabIndex={0}
        className="favorite-toggle"
        title={item.is_favorite ? 'Remove favorite' : 'Add favorite'}
        onClick={(event) => {
          event.stopPropagation();
          onFavoriteToggle(item);
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            event.stopPropagation();
            onFavoriteToggle(item);
          }
        }}
      >
        <Star size={15} fill={item.is_favorite ? 'currentColor' : 'none'} />
      </span>
    </button>
  );
}
