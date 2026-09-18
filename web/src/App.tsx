import { useEffect, useState } from "react";
import BackgroundGlow from "./components/BackgroundGlow";
import StatBar from "./components/StatBar";
import SubTabRow from "./components/SubTabRow";
import TopNav from "./components/TopNav";
import { api } from "./lib/api";
import type { Overview } from "./lib/types";
import Anecdotes from "./pages/analysis/Anecdotes";
import CoversEncores from "./pages/analysis/CoversEncores";
import Heatmaps from "./pages/analysis/Heatmaps";
import Models from "./pages/analysis/Models";
import ClusterExplorer from "./pages/analysis/ClusterExplorer";
import SetlistTrend from "./pages/analysis/SetlistTrend";
import SongExplorer from "./pages/analysis/SongExplorer";
import SongMap from "./pages/analysis/SongMap";
import Tours from "./pages/analysis/Tours";
import TransitionGraph from "./pages/analysis/TransitionGraph";
import VenueMap from "./pages/analysis/VenueMap";
import Landing from "./pages/Landing";
import ConcertLength from "./pages/predictions/ConcertLength";
import Comeback from "./pages/predictions/Comeback";
import Encore from "./pages/predictions/Encore";
import NextCountry from "./pages/predictions/NextCountry";
import RunningOrder from "./pages/predictions/RunningOrder";
import NextDate from "./pages/predictions/NextDate";
import NextSetlist from "./pages/predictions/NextSetlist";
import SongRole from "./pages/predictions/SongRole";

const PREDICTION_TABS = [
  { index: "01", title: "Next Setlist" },
  { index: "02", title: "Concert Length" },
  { index: "03", title: "Song Role" },
  { index: "04", title: "Next Date" },
  { index: "05", title: "Next Country" },
  { index: "06", title: "Running Order" },
  { index: "07", title: "Encore" },
  { index: "08", title: "Coming Back" },
];

const ANALYSIS_TABS = [
  { index: "01", title: "Venue Map" },
  { index: "02", title: "Setlist Trend" },
  { index: "03", title: "Cluster Explorer" },
  { index: "04", title: "Transition Graph" },
  { index: "05", title: "Anecdotes" },
  { index: "06", title: "Tours" },
  { index: "07", title: "Covers & Encores" },
  { index: "08", title: "Song Map" },
  { index: "09", title: "Heatmaps" },
  { index: "10", title: "Models" },
  { index: "11", title: "Song Explorer" },
];

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [activeTab, setActiveTab] = useState<"predictions" | "analysis">("predictions");
  const [subTabIndex, setSubTabIndex] = useState(0);
  const [overview, setOverview] = useState<Overview | null>(null);

  useEffect(() => {
    api.overview().then(setOverview).catch(() => {});
  }, []);

  if (showLanding) {
    return (
      <>
        <BackgroundGlow />
        <Landing
          overview={overview}
          onExplore={() => {
            setActiveTab("predictions");
            setSubTabIndex(0);
            setShowLanding(false);
          }}
        />
      </>
    );
  }

  const tabs = activeTab === "predictions" ? PREDICTION_TABS : ANALYSIS_TABS;
  const accent = activeTab === "predictions" ? "violet" : "ember";

  return (
    <div className="pb-16">
      <BackgroundGlow />
      <TopNav
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          setSubTabIndex(0);
        }}
        onHome={() => setShowLanding(true)}
        shows={overview?.concerts_logged ?? 0}
        yearsStart={overview?.years_start ?? 0}
        yearsEnd={overview?.years_end ?? 0}
      />
      <SubTabRow tabs={tabs} activeIndex={subTabIndex} onChange={setSubTabIndex} accent={accent} />
      <main className="mx-auto max-w-[112rem] px-8 py-10">
        {activeTab === "predictions" && subTabIndex === 0 && <NextSetlist />}
        {activeTab === "predictions" && subTabIndex === 1 && <ConcertLength />}
        {activeTab === "predictions" && subTabIndex === 2 && <SongRole />}
        {activeTab === "predictions" && subTabIndex === 3 && <NextDate />}
        {activeTab === "predictions" && subTabIndex === 4 && <NextCountry />}
              {activeTab === "predictions" && subTabIndex === 5 && <RunningOrder />}
              {activeTab === "predictions" && subTabIndex === 6 && <Encore />}
              {activeTab === "predictions" && subTabIndex === 7 && <Comeback />}
        {activeTab === "analysis" && subTabIndex === 0 && <VenueMap />}
        {activeTab === "analysis" && subTabIndex === 1 && <SetlistTrend />}
        {activeTab === "analysis" && subTabIndex === 2 && <ClusterExplorer />}
        {activeTab === "analysis" && subTabIndex === 3 && <TransitionGraph />}
        {activeTab === "analysis" && subTabIndex === 4 && <Anecdotes />}
        {activeTab === "analysis" && subTabIndex === 5 && <Tours />}
        {activeTab === "analysis" && subTabIndex === 6 && <CoversEncores />}
        {activeTab === "analysis" && subTabIndex === 7 && <SongMap />}
        {activeTab === "analysis" && subTabIndex === 8 && <Heatmaps />}
        {activeTab === "analysis" && subTabIndex === 9 && <Models />}
        {activeTab === "analysis" && subTabIndex === 10 && <SongExplorer />}
      </main>
      {overview && (
        <StatBar
          stats={[
            { label: "setlist accuracy", value: `${Math.round((overview.setlist_accuracy ?? 0) * 100)}%` },
            { label: "length MAE", value: `${overview.length_mae_songs ?? "N/A"} songs` },
            {
              label: "",
              value: `${overview.concerts_logged} concerts · ${overview.venues_mapped} venues · ${overview.countries} countries`,
            },
          ]}
        />
      )}
    </div>
  );
}
