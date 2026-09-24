import { animate, motion, useInView, useScroll, useTransform } from "motion/react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import coverCurrents from "../assets/cover-currents.jpg";
import coverDeadbeat from "../assets/cover-deadbeat.jpg";
import coverInnerspeaker from "../assets/cover-innerspeaker.jpg";
import coverLonerism from "../assets/cover-lonerism.jpg";
import coverSlowRush from "../assets/cover-slowrush.jpg";
import TourWave from "../app/TourWave";
import TrackList from "../app/TrackList";
import Waveform from "../app/Waveform";
import { pathOf, routesOf } from "../app/routes";
import { api } from "../lib/api";
import { PHOTOS } from "../lib/photos";
import type { Overview, SongPrediction } from "../lib/types";

interface LandingProps {
  overview: Overview | null;
  navigate: (path: string) => void;
}

const DISCOGRAPHY = [
  { title: "Innerspeaker", year: "2010", cover: coverInnerspeaker },
  { title: "Lonerism", year: "2012", cover: coverLonerism },
  { title: "Currents", year: "2015", cover: coverCurrents },
  { title: "The Slow Rush", year: "2020", cover: coverSlowRush },
  { title: "Deadbeat", year: "2025", cover: coverDeadbeat },
];

const ease = [0.22, 1, 0.36, 1] as const;

function Letters({ text, className, delay = 0 }: { text: string; className: string; delay?: number }) {
  return (
    <span className={`block overflow-hidden pb-[0.04em] ${className}`} aria-hidden>
      {text.split("").map((ch, i) => (
        <motion.span
          key={i}
          className="inline-block"
          initial={{ y: "105%", rotate: 8 }}
          animate={{ y: "0%", rotate: 0 }}
          transition={{ duration: 1.1, delay: delay + i * 0.05, ease }}
        >
          {ch}
        </motion.span>
      ))}
    </span>
  );
}

function CountUp({ value, suffix = "" }: { value: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10% 0px" });
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (!inView) return;
    const controls = animate(0, value, { duration: 1.6, ease, onUpdate: (v) => setShown(Math.round(v)) });
    return () => controls.stop();
  }, [inView, value]);
  return (
    <span ref={ref} className="tabular-nums">
      {shown}
      {suffix}
    </span>
  );
}

// A record on the platter, with a photograph for its label. Grooves are a repeating radial
// gradient; the sheen is a conic gradient that stays put while the disc turns under it.
function Vinyl({ className = "" }: { className?: string }) {
  return (
    <div className={`group relative aspect-square ${className}`}>
      {[0, 1.6, 3.2].map((d) => (
        <span
          key={d}
          className="pulse-ring absolute inset-0 rounded-full border border-violet-light/40"
          style={{ animationDelay: `${d}s` }}
        />
      ))}
      <div className="vinyl-spin absolute inset-0 rounded-full bg-[#0b070d] shadow-[0_40px_120px_-20px_rgba(0,0,0,0.9)] [background-image:repeating-radial-gradient(circle_at_center,rgba(255,255,255,0.045)_0_1px,transparent_1px_4px)]">
        <img
          src={PHOTOS.guitaristConfetti.src}
          alt=""
          className="melt-hover absolute left-1/2 top-1/2 h-[38%] w-[38%] -translate-x-1/2 -translate-y-1/2 rounded-full object-cover"
        />
        <span className="absolute left-1/2 top-1/2 h-[3%] w-[3%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-bg" />
      </div>
      <div className="pointer-events-none absolute inset-0 rounded-full [background:conic-gradient(from_200deg,transparent_0deg,rgba(255,255,255,0.10)_40deg,transparent_90deg,transparent_180deg,rgba(255,255,255,0.07)_220deg,transparent_270deg)]" />
    </div>
  );
}

// The songs the model rates most likely for the next show, scrolling past like a ticker. Real
// predictions from the API; nothing is shown until they arrive.
function Marquee({ songs }: { songs: SongPrediction[] }) {
  const row = (copy: string) => songs.map((s) => (
    <span key={`${copy}-${s.song_id}`} aria-hidden={copy === "b"} className="flex shrink-0 items-baseline gap-4 pr-12">
      <span className="font-serif text-[clamp(2rem,4.5vw,4.2rem)] italic leading-none text-white">{s.song_name}</span>
      <span className="font-mono text-sm tabular-nums text-violet-light">{Math.round(s.probability * 100)}%</span>
      <span className="pl-8 text-2xl text-white/25">✺</span>
    </span>
  ));
  return (
    <div className="relative overflow-hidden py-6 [mask-image:linear-gradient(90deg,transparent,#000_8%,#000_92%,transparent)]">
      <div className="marquee-track flex w-max" style={{ ["--marquee-duration" as string]: `${songs.length * 5}s` }}>
        {row("a")}
        {row("b")}
      </div>
    </div>
  );
}

export default function Landing({ overview, navigate }: LandingProps) {
  const hero = useRef<HTMLElement>(null);
  const [likely, setLikely] = useState<SongPrediction[]>([]);
  const { scrollYProgress } = useScroll({ target: hero, offset: ["start start", "end start"] });
  const discY = useTransform(scrollYProgress, [0, 1], ["0%", "35%"]);
  const discRotate = useTransform(scrollYProgress, [0, 1], [0, 90]);
  const titleX = useTransform(scrollYProgress, [0, 1], ["0%", "-12%"]);
  const fade = useTransform(scrollYProgress, [0, 0.7], [1, 0]);

  useEffect(() => {
    api
      .nextSetlist()
      .then((songs) => setLikely([...songs].sort((a, b) => b.probability - a.probability).slice(0, 14)))
      .catch(() => {});
  }, []);

  return (
    <div className="overflow-x-clip pb-24">
      {/* Poster */}
      <section ref={hero} className="relative flex min-h-[100svh] flex-col justify-end overflow-hidden px-5 pb-10 pt-28 sm:px-10">
        <motion.div
          className="absolute -right-[18vw] top-[8vh] w-[min(78vw,62rem)] sm:-right-[8vw] lg:top-[4vh]"
          style={{ y: discY, rotate: discRotate }}
          initial={{ opacity: 0, x: 120, rotate: -40 }}
          animate={{ opacity: 1, x: 0, rotate: 0 }}
          transition={{ duration: 1.8, ease }}
        >
          <Vinyl />
        </motion.div>

        <Waveform className="pointer-events-none absolute inset-x-0 bottom-0 h-40 opacity-80" traces={4} />

        <motion.div style={{ opacity: fade }} className="relative">
          <motion.p
            className="mb-6 max-w-sm font-serif text-2xl italic leading-snug text-white/80 sm:text-3xl"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, delay: 0.9, ease }}
          >
            Tame Impala, live, {overview?.years_start ?? 2008} to {overview?.years_end ?? 2026}. Every setlist, and what
            the next one might hold.
          </motion.p>
          <motion.h1
            style={{ x: titleX }}
            className="chroma font-hero text-[clamp(3rem,13.2vw,15rem)] font-extrabold leading-[0.82] tracking-[-0.04em]"
            aria-label="Undercurrents"
          >
            <Letters text="UNDER" className="text-white" delay={0.2} />
            <Letters text="CURRENTS" className="text-white" delay={0.45} />
          </motion.h1>

          <motion.div
            className="mt-10 flex flex-wrap items-center gap-4"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, delay: 1.2, ease }}
          >
            <button
              type="button"
              onClick={() => navigate(pathOf(routesOf("predictions")[0]))}
              className="group relative overflow-hidden rounded-full bg-white px-7 py-3.5 text-[15px] font-medium text-ink outline-none focus-visible:ring-2 focus-visible:ring-violet-light focus-visible:ring-offset-4 focus-visible:ring-offset-ink"
            >
              <span className="absolute inset-0 origin-left scale-x-0 bg-gradient-to-r from-violet-light to-ember-light transition-transform duration-500 ease-out group-hover:scale-x-100" />
              <span className="relative">Drop the needle</span>
            </button>
            {overview && (
              <p className="text-sm text-white/55">
                <span className="text-white">{overview.concerts_logged}</span> shows ·{" "}
                <span className="text-white">{overview.venues_mapped}</span> venues ·{" "}
                <span className="text-white">{overview.countries}</span> countries
              </p>
            )}
          </motion.div>
        </motion.div>
      </section>

      {/* Ticker of the next show's likeliest songs */}
      {likely.length > 0 && (
        <section className="border-y border-white/10 bg-ink/30 backdrop-blur-sm">
          <p className="px-5 pt-5 text-sm text-white/45 sm:px-10">Most likely at the next show, according to the setlist model</p>
          <Marquee songs={likely} />
        </section>
      )}

      {/* The record in one sentence */}
      {overview && (
        <section className="mx-auto max-w-[1400px] px-5 pt-32 sm:px-10">
          <motion.p
            className="max-w-5xl font-display text-[clamp(1.8rem,3.6vw,3.4rem)] font-medium leading-[1.12] tracking-tight text-white/40"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 1, ease }}
          >
            <span className="text-white"><CountUp value={overview.concerts_logged} /> nights</span> in{" "}
            <span className="text-white"><CountUp value={overview.venues_mapped} /> rooms</span>, sorted into{" "}
            <span className="font-serif italic text-white"><CountUp value={overview.setlist_clusters} /> kinds of night</span>. Asked to
            name as many songs as a held-out show really had, the model gets{" "}
            <span className="bg-gradient-to-r from-violet-light to-ember-light bg-clip-text text-transparent">
              <CountUp value={Math.round((overview.setlist_accuracy ?? 0) * 100)} suffix="%" />
            </span>{" "}
            of them.
          </motion.p>
        </section>
      )}

      {/* Eighteen years as an audio file */}
      <section className="mx-auto max-w-[1400px] px-5 pt-32 sm:px-10">
        <h2 className="chroma font-hero text-[clamp(2rem,5vw,4.5rem)] font-extrabold uppercase leading-[0.9] tracking-tight">
          The tour<span className="font-serif font-normal normal-case italic text-white/55">, as a waveform</span>
        </h2>
        <div className="mt-10">
          <TourWave />
        </div>
      </section>

      {/* Both sides, as tracklists */}
      <section className="mx-auto grid max-w-[1400px] gap-20 px-5 pt-32 sm:px-10 lg:grid-cols-2">
        <InView>
          <TrackList side="predictions" />
        </InView>
        <InView>
          <TrackList side="analysis" size="lg" />
        </InView>
      </section>

      {/* Five records */}
      <section className="mx-auto max-w-[1400px] px-5 pt-36 sm:px-10">
        <h2 className="chroma font-hero text-[clamp(2rem,5vw,4.5rem)] font-extrabold uppercase leading-[0.9] tracking-tight">
          Five records<span className="font-serif font-normal normal-case italic text-white/50">, five eras</span>
        </h2>
        <div className="mt-14 grid grid-cols-2 gap-x-6 gap-y-12 sm:grid-cols-3 lg:grid-cols-5">
          {DISCOGRAPHY.map((album, i) => (
            <motion.figure
              key={album.title}
              className="group"
              initial={{ opacity: 0, y: 60, rotate: i % 2 ? 4 : -4 }}
              whileInView={{ opacity: 1, y: 0, rotate: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 1, delay: i * 0.08, ease }}
            >
              <div className="relative aspect-square">
                {/* the disc slides out of the sleeve on hover */}
                <div className="absolute inset-[4%] rounded-full bg-[#0b070d] transition-transform duration-700 ease-out [background-image:repeating-radial-gradient(circle_at_center,rgba(255,255,255,0.05)_0_1px,transparent_1px_4px)] group-hover:translate-x-[38%]">
                  <img src={album.cover} alt="" className="absolute left-1/2 top-1/2 h-[36%] w-[36%] -translate-x-1/2 -translate-y-1/2 rounded-full object-cover" />
                </div>
                <img
                  src={album.cover}
                  alt={`${album.title} album cover`}
                  className="relative h-full w-full rounded-sm object-cover shadow-2xl shadow-black/60"
                />
              </div>
              <figcaption className="mt-4 flex items-baseline justify-between">
                <span className="font-display text-base text-white">{album.title}</span>
                <span className="font-mono text-xs text-white/40">{album.year}</span>
              </figcaption>
            </motion.figure>
          ))}
        </div>
      </section>

      <Waveform className="mt-36 h-28" traces={3} from="#ff9270" to="#e2a6ff" />

      <footer className="mx-auto mt-10 flex max-w-[1400px] flex-wrap items-center justify-between gap-4 border-t border-white/10 px-5 pt-8 text-sm text-white/40 sm:px-10">
        <span>Setlists from setlist.fm, audio features from AcousticBrainz, weather from Open-Meteo.</span>
        <a
          href="https://github.com/LenouvelLouis/Undercurrents"
          className="rounded text-white/60 outline-none hover:text-white focus-visible:ring-2 focus-visible:ring-white/60"
        >
          Source on GitHub
        </a>
      </footer>
    </div>
  );
}

// Tracklists animate their rows on mount, so on the landing they wait until scrolled into view.
function InView({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const seen = useInView(ref, { once: true, margin: "-120px" });
  return <div ref={ref} className="min-h-[20rem]">{seen && children}</div>;
}
