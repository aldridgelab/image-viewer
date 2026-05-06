import { Download, Search, Shuffle, Star } from 'lucide-react';
import type {
  ViewerChannelColor,
  ViewerCompositeChannels,
  ViewerRenderMode,
} from '../api/types';

interface BrowserToolbarProps {
  search: string;
  limit: number;
  favoritesOnly: boolean;
  isLoading: boolean;
  renderMode: ViewerRenderMode;
  compositeChannels: ViewerCompositeChannels;
  channelNames: string[];
  channelCount: number;
  onSearchChange: (value: string) => void;
  onLimitChange: (value: number) => void;
  onFavoritesOnlyChange: (value: boolean) => void;
  onRenderModeChange: (value: ViewerRenderMode) => void;
  onCompositeChannelChange: (color: ViewerChannelColor, value: number | null) => void;
  onRandomize: () => void;
  onExportContactSheet: () => void;
}

const COMPOSITE_COLORS: ViewerChannelColor[] = ['red', 'green', 'blue'];

export function BrowserToolbar({
  search,
  limit,
  favoritesOnly,
  isLoading,
  renderMode,
  compositeChannels,
  channelNames,
  channelCount,
  onSearchChange,
  onLimitChange,
  onFavoritesOnlyChange,
  onRenderModeChange,
  onCompositeChannelChange,
  onRandomize,
  onExportContactSheet,
}: BrowserToolbarProps) {
  return (
    <div className="browser-toolbar">
      <div className="search-box">
        <Search size={17} />
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search filename"
        />
      </div>
      <label className="limit-control">
        <span>Limit</span>
        <input
          type="number"
          min={1}
          max={1000}
          value={limit}
          onChange={(event) => onLimitChange(Math.max(1, Number(event.target.value) || 120))}
        />
      </label>
      <label className="mode-control">
        <span>View</span>
        <select
          value={renderMode}
          onChange={(event) => onRenderModeChange(event.target.value as ViewerRenderMode)}
          title="Grid render mode"
        >
          <option value="single">Single</option>
          <option value="composite">RGB</option>
        </select>
      </label>
      {renderMode === 'composite' &&
        COMPOSITE_COLORS.map((color) => (
          <label className="mode-control mode-control--compact" key={color}>
            <span className={`channel-color-label channel-color-label--${color}`}>
              {color.slice(0, 1).toUpperCase()}
            </span>
            <select
              value={compositeChannels[color] ?? ''}
              onChange={(event) => {
                const value = event.target.value;
                onCompositeChannelChange(color, value === '' ? null : Number(value));
              }}
              title={`${color} composite channel`}
            >
              <option value="">Off</option>
              {Array.from({ length: channelCount }).map((_, index) => (
                <option value={index} key={index}>
                  {channelNames[index] || `Ch ${index + 1}`}
                </option>
              ))}
            </select>
          </label>
        ))}
      <button
        className={`text-button ${favoritesOnly ? 'is-active amber' : ''}`}
        type="button"
        onClick={() => onFavoritesOnlyChange(!favoritesOnly)}
      >
        <Star size={16} fill={favoritesOnly ? 'currentColor' : 'none'} />
        Favorites
      </button>
      <button className="text-button" type="button" onClick={onRandomize} disabled={isLoading}>
        <Shuffle size={16} />
        Shuffle
      </button>
      <button
        className="text-button"
        type="button"
        onClick={onExportContactSheet}
        disabled={isLoading}
        title="Export contact sheet"
      >
        <Download size={16} />
        Export
      </button>
    </div>
  );
}
