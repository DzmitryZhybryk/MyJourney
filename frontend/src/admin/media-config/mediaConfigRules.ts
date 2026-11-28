import type {
  ImageFormatEnum,
  ImageKindRules,
  MediaConfigSnapshot,
  VideoFormatEnum,
  VideoKindRules,
} from "../../api/sdk";

export type MediaFormat = ImageFormatEnum | VideoFormatEnum;
export type KindRules = ImageKindRules | VideoKindRules;
export type RuleField = "maxSizeBytes" | "formats" | "minSide";

const BYTES_PER_MEGABYTE = 1024 * 1024;

/** Every format the backend accepts, in the order the chips are shown. */
export const IMAGE_FORMATS: readonly ImageFormatEnum[] = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/heic",
  "image/heif",
];
export const VIDEO_FORMATS: readonly VideoFormatEnum[] = ["video/mp4", "video/quicktime"];

/** What a user calls the format: the file extension people see, not the MIME type. */
export const FORMAT_LABELS: Readonly<Record<MediaFormat, string>> = {
  "image/jpeg": "JPEG",
  "image/png": "PNG",
  "image/webp": "WebP",
  "image/heic": "HEIC",
  "image/heif": "HEIF",
  "video/mp4": "MP4",
  "video/quicktime": "MOV",
};

export function bytesToMegabytes(bytes: number): number {
  return Math.round((bytes / BYTES_PER_MEGABYTE) * 10) / 10;
}

export function megabytesToBytes(megabytes: number): number {
  return Math.round(megabytes * BYTES_PER_MEGABYTE);
}

function haveSameItems(left: readonly string[], right: readonly string[]): boolean {
  return left.length === right.length && left.every((item) => right.includes(item));
}

/** Whether one field of a kind differs between the saved config and the draft; formats compare as sets. */
export function isRuleChanged(saved: KindRules, draft: KindRules, field: RuleField): boolean {
  if (field === "formats") {
    return !haveSameItems(saved.formats, draft.formats);
  }

  if (field === "minSide") {
    return "minSide" in saved && "minSide" in draft && saved.minSide !== draft.minSide;
  }

  return saved.maxSizeBytes !== draft.maxSizeBytes;
}

const RULE_FIELDS: readonly RuleField[] = ["maxSizeBytes", "formats", "minSide"];
const KINDS: readonly (keyof MediaConfigSnapshot)[] = ["avatar", "journeyPhoto", "journeyVideo"];

/** How many values the draft changes against the saved config. */
export function countChangedRules(saved: MediaConfigSnapshot, draft: MediaConfigSnapshot): number {
  return KINDS.reduce(
    (total, kind) =>
      total + RULE_FIELDS.filter((field) => isRuleChanged(saved[kind], draft[kind], field)).length,
    0,
  );
}
