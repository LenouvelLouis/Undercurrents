import coverCurrents from "../assets/cover-currents.jpg";
import coverDeadbeat from "../assets/cover-deadbeat.jpg";
import coverInnerspeaker from "../assets/cover-innerspeaker.jpg";
import coverLonerism from "../assets/cover-lonerism.jpg";
import coverSlowRush from "../assets/cover-slowrush.jpg";
import PhotoPanel from "../components/PhotoPanel";
import { PHOTOS } from "../lib/photos";
import type { Overview } from "../lib/types";

interface LandingProps {
  overview: Overview | null;
  onExplore: () => void;
}

const DISCOGRAPHY = [
  { title: "Innerspeaker", year: "2010", cover: coverInnerspeaker },
  { title: "Lonerism", year: "2012", cover: coverLonerism },
  { title: "Currents", year: "2015", cover: coverCurrents },
  { title: "The Slow Rush", year: "2020", cover: coverSlowRush },
  { title: "Deadbeat", year: "2025", cover: coverDeadbeat },
];

export default function Landing({ overview, onExplore }: LandingProps) {
  const stats = overview
    ? [
        { value: String(overview.concerts_logged), label: "concerts logged" },
        { value: `${overview.years_end - overview.years_start}`, label: `years, ${overview.years_start}-${overview.years_end}` },
        { value: String(overview.venues_mapped), label: "venues mapped" },
        { value: String(overview.countries), label: "countries" },
        { value: `${Math.round((overview.setlist_accuracy ?? 0) * 100)}%`, label: "setlist accuracy" },
        { value: String(overview.setlist_clusters), label: "setlist clusters" },
      ]
    : [];

  return (
    <div className="pb-24">
      {/* Full-bleed cinematic hero (photo as backdrop, copy overlaid bottom-left) */}
      <section className="relative h-[88vh] min-h-[620px] w-full overflow-hidden border-b border-white/10">
        <img
          src={PHOTOS.singerConfetti.src}
          alt={PHOTOS.singerConfetti.alt}
          className="absolute inset-0 h-full w-full scale-105 object-cover"
          style={{ objectPosition: "center 45%" }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-ink via-ink/55 to-ink/20" />
        <div className="absolute inset-0 bg-gradient-to-r from-ink/85 via-ink/25 to-transparent" />
        <div className="grain-overlay" />

        <div className="absolute right-8 top-8 text-right">
          <p className="font-mono text-[10px] uppercase tracking-widest text-white/50">Kevin Parker &amp; band</p>
        </div>

        <div className="absolute inset-x-0 bottom-0 px-8 pb-14 sm:px-12">
          <div className="mx-auto max-w-[112rem]">
            <p className="font-mono text-xs tracking-[0.3em] text-violet-light">TAME IMPALA TOUR INTELLIGENCE</p>
            <h1 className="mt-4 font-hero text-6xl leading-[0.92] sm:text-8xl">
              <span className="block font-extrabold text-white">UNDER</span>
              <span className="block font-semibold text-white/50">CURRENTS</span>
            </h1>
            <p className="mt-6 max-w-lg text-lg text-white/70">
              Eighteen years of real setlists, venues and tours, run through predictive models:
              probabilities and honest uncertainty, not a single guess.
            </p>
            <button
              onClick={onExplore}
              className="mt-8 w-fit rounded-full bg-gradient-to-r from-violet to-violet-light px-6 py-3 font-medium text-ink shadow-glow-violet transition-transform hover:scale-[1.02]"
            >
              Explore the predictions →
            </button>
          </div>
        </div>
      </section>

      {/* Editorial stat strip (full-width band, independent of the hero column) */}
      {stats.length > 0 && (
        <section className="border-b border-white/10 bg-white/[0.02]">
          <div className="mx-auto grid max-w-[112rem] grid-cols-2 divide-x divide-y divide-white/10 px-8 sm:grid-cols-3 sm:divide-y-0 lg:grid-cols-6">
            {stats.map((stat) => (
              <div key={stat.label} className="px-2 py-8 text-center sm:px-4">
                <div className="font-display text-3xl font-bold text-white">{stat.value}</div>
                <div className="mt-1 font-mono text-[11px] text-white/40">{stat.label}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* From the archive: the photographs the rest of the site is built around, shown
          once at full size before the data pages start quoting them a frame at a time. */}
      <section className="mx-auto max-w-[112rem] px-8 pt-20">
        <div className="flex items-baseline justify-between border-b border-white/10 pb-4">
          <p className="font-mono text-xs uppercase tracking-widest text-white/40">From the archive</p>
          <p className="font-mono text-xs text-white/30">on the road</p>
        </div>
        <div className="mt-10 grid grid-cols-4 gap-6">
          <PhotoPanel photo={PHOTOS.silhouetteLasers} accent="violet" className="col-span-4 h-[22rem] lg:col-span-2" focus="center 50%" />
          <PhotoPanel photo={PHOTOS.stageRainbowLights} accent="violet" className="col-span-2 h-[22rem] lg:col-span-1" focus="center 40%" style={{ animationDelay: "0.06s" }} />
          <PhotoPanel photo={PHOTOS.arenaAerial} accent="violet" className="col-span-2 h-[22rem] lg:col-span-1" focus="center 35%" style={{ animationDelay: "0.12s" }} />
          <PhotoPanel photo={PHOTOS.synthTable} accent="ember" className="col-span-2 h-[20rem] lg:col-span-1" focus="center 30%" style={{ animationDelay: "0.18s" }} />
          <PhotoPanel photo={PHOTOS.backyardPortrait} accent="ember" className="col-span-2 h-[20rem] lg:col-span-1" focus="center 22%" style={{ animationDelay: "0.24s" }} />
          <PhotoPanel photo={PHOTOS.guitaristConfetti} accent="ember" className="col-span-4 h-[20rem] lg:col-span-2" focus="center 40%" style={{ animationDelay: "0.3s" }} />
        </div>
      </section>

      {/* Discography shelf (staggered, leaning records rather than a flat filmstrip) */}
      <section className="mx-auto max-w-[112rem] px-8 pt-20">
        <div className="flex items-baseline justify-between border-b border-white/10 pb-4">
          <p className="font-mono text-xs uppercase tracking-widest text-white/40">
            The five eras this model was trained on
          </p>
          <p className="font-mono text-xs text-white/30">01–05</p>
        </div>
        <div className="mt-12 flex flex-wrap items-end justify-center gap-x-8 gap-y-12 sm:justify-between">
          {DISCOGRAPHY.map((album, i) => (
            <div
              key={album.title}
              className="group w-36 shrink-0 transition-transform duration-300 hover:-translate-y-2 sm:w-[17%]"
              style={{
                transform: `rotate(${i % 2 === 0 ? -2 : 2}deg) translateY(${i % 2 === 1 ? 18 : 0}px)`,
              }}
            >
              <div className="relative aspect-square w-full overflow-hidden rounded-xl border border-white/10 shadow-xl shadow-black/40">
                <img
                  src={album.cover}
                  alt={`${album.title} album cover`}
                  className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                />
                <span className="absolute left-2 top-2 rounded-full bg-ink/70 px-2 py-0.5 font-mono text-[9px] text-white/60 backdrop-blur-sm">
                  {String(i + 1).padStart(2, "0")}
                </span>
              </div>
              <div className="mt-3">
                <div className="font-display text-sm font-bold text-white">{album.title}</div>
                <div className="font-mono text-[10px] text-white/40">{album.year}</div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
