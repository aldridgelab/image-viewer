import { Eye, FolderOpen, Loader2 } from 'lucide-react';
import type { ViewerInspectResponse } from '../api/types';

interface SetupPanelProps {
  isOpen: boolean;
  directory: string;
  pattern: string;
  channelNames: string[];
  defaultChannel: number;
  inspectResult: ViewerInspectResponse | null;
  isInspecting: boolean;
  isApplying: boolean;
  onDirectoryChange: (value: string) => void;
  onPatternChange: (value: string) => void;
  onInspect: () => void;
  onApply: () => void;
  onChannelNameChange: (index: number, value: string) => void;
  onDefaultChannelChange: (index: number) => void;
}

export function SetupPanel({
  isOpen,
  directory,
  pattern,
  channelNames,
  defaultChannel,
  inspectResult,
  isInspecting,
  isApplying,
  onDirectoryChange,
  onPatternChange,
  onInspect,
  onApply,
  onChannelNameChange,
  onDefaultChannelChange,
}: SetupPanelProps) {
  const channelNamesComplete =
    inspectResult !== null &&
    channelNames.length === inspectResult.channel_count &&
    channelNames.every((name) => name.trim().length > 0);

  return (
    <section className={`setup-panel ${isOpen ? 'is-open' : ''}`}>
      <div className="setup-grid">
        <label>
          <span>Directory Path</span>
          <input
            value={directory}
            onChange={(event) => onDirectoryChange(event.target.value)}
            placeholder="/path/to/tiff/files"
          />
        </label>
        <label>
          <span>File Pattern</span>
          <input
            value={pattern}
            onChange={(event) => onPatternChange(event.target.value)}
            placeholder="*.tif"
          />
        </label>
        <button
          className="primary-button"
          type="button"
          onClick={onInspect}
          disabled={isInspecting || !directory.trim()}
        >
          {isInspecting ? <Loader2 size={17} className="spin" /> : <Eye size={17} />}
          Inspect
        </button>
      </div>

      {inspectResult && (
        <div className="inspect-result">
          <div className="inspect-result__summary">
            <strong>{inspectResult.total_images}</strong> files
            <strong>{inspectResult.channel_count}</strong> channels
            {inspectResult.axes && <strong>{inspectResult.axes}</strong>}
          </div>
          {inspectResult.channel_count > 0 && (
            <>
              <div className="channel-name-grid">
                {channelNames.map((name, index) => (
                  <label key={index}>
                    <span>Channel {index + 1}</span>
                    <input
                      value={name}
                      onChange={(event) => onChannelNameChange(index, event.target.value)}
                    />
                  </label>
                ))}
              </div>
              <div className="segmented-control">
                {channelNames.map((name, index) => (
                  <button
                    type="button"
                    key={index}
                    className={defaultChannel === index ? 'is-selected' : ''}
                    onClick={() => onDefaultChannelChange(index)}
                  >
                    {name || `Channel ${index + 1}`}
                  </button>
                ))}
              </div>
            </>
          )}
          {inspectResult.total_images > 0 && (
            <button
              className="primary-button"
              type="button"
              onClick={onApply}
              disabled={isApplying || !channelNamesComplete}
            >
              {isApplying ? <Loader2 size={17} className="spin" /> : <FolderOpen size={17} />}
              Apply
            </button>
          )}
        </div>
      )}
    </section>
  );
}
