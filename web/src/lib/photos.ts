import artistRedSeats from "../assets/artist-photo.jpg";
import arenaAerial from "../assets/concert/concert-arena-aerial.jpg";
import arenaLasersWide from "../assets/concert/concert-arena-lasers-wide.jpg";
import guitaristClose from "../assets/concert/concert-guitarist-close.jpg";
import guitaristConfetti from "../assets/concert/concert-guitarist-confetti.jpg";
import roundStageAerial from "../assets/concert/concert-round-stage-aerial.jpg";
import roundStageOverhead from "../assets/concert/concert-round-stage-overhead.jpg";
import silhouetteLasers from "../assets/concert/concert-silhouette-lasers.jpg";
import singerBlur from "../assets/concert/concert-singer-blur.jpg";
import singerConfetti from "../assets/concert/concert-singer-confetti.jpg";
import stageRainbowLights from "../assets/concert/concert-stage-rainbow-lights.jpg";
import synthTable from "../assets/concert/concert-synth-table.jpg";
import backyardPortrait from "../assets/concert/portrait-backyard.jpg";

export interface Photo {
  src: string;
  /** Shown on the page, under or over the image. Kept short so it fits a caption line. */
  caption: string;
  /** Longer form, used as the alt attribute for screen readers. */
  alt: string;
  shape: "portrait" | "landscape";
}

// Every photograph in the archive, captioned once here so the same picture is never
// described two different ways on two different pages. Pages pull from this registry
// instead of importing image files directly, which is also what keeps the spread below
// honest: it is easy to see, in one place, that no page repeats a photo and that the
// album sleeves are no longer standing in as filler.
export const PHOTOS = {
  guitaristConfetti: {
    src: guitaristConfetti,
    caption: "Confetti over the guitar solo",
    alt: "Kevin Parker playing guitar as confetti falls across the stage",
    shape: "landscape",
  },
  singerBlur: {
    src: singerBlur,
    caption: "Caught mid-move, long exposure",
    alt: "Long exposure of the singer blurred in motion on stage",
    shape: "portrait",
  },
  singerConfetti: {
    src: singerConfetti,
    caption: "Confetti burst over the front rows",
    alt: "Confetti bursting over the crowd at the front of the stage",
    shape: "landscape",
  },
  arenaAerial: {
    src: arenaAerial,
    caption: "The round stage from the rafters",
    alt: "Aerial view of the round stage inside a packed arena",
    shape: "portrait",
  },
  stageRainbowLights: {
    src: stageRainbowLights,
    caption: "A wall of colour behind the band",
    alt: "The band on stage in front of a rainbow-lit wall of bulbs",
    shape: "portrait",
  },
  guitaristClose: {
    src: guitaristClose,
    caption: "Close on the guitar, confetti still falling",
    alt: "Close view of Kevin Parker playing guitar under falling confetti",
    shape: "portrait",
  },
  backyardPortrait: {
    src: backyardPortrait,
    caption: "Off tour, in the backyard",
    alt: "Kevin Parker in sunglasses standing in a sunlit backyard",
    shape: "portrait",
  },
  roundStageAerial: {
    src: roundStageAerial,
    caption: "Round stage, lit from above",
    alt: "Aerial view of the round stage lit in colour",
    shape: "portrait",
  },
  silhouetteLasers: {
    src: silhouetteLasers,
    caption: "Silhouettes against the lasers",
    alt: "The band silhouetted against crossing laser beams",
    shape: "landscape",
  },
  arenaLasersWide: {
    src: arenaLasersWide,
    caption: "Lasers across the full room",
    alt: "Laser beams crossing the full width of an arena show",
    shape: "landscape",
  },
  roundStageOverhead: {
    src: roundStageOverhead,
    caption: "Synths and lamps, seen from overhead",
    alt: "Overhead view of the synth-and-lamp round stage setup",
    shape: "portrait",
  },
  synthTable: {
    src: synthTable,
    caption: "Leaning over the synth table",
    alt: "Kevin Parker leaning over a table of synthesisers on stage",
    shape: "portrait",
  },
  artistRedSeats: {
    src: artistRedSeats,
    caption: "Red seats, empty room",
    alt: "Kevin Parker reclining across red cinema seats",
    shape: "landscape",
  },
} satisfies Record<string, Photo>;

export type PhotoKey = keyof typeof PHOTOS;
