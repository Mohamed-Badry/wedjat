export const uiState = $state({
  operations: {
    selectedStationId: 'beni_suef',
    selectedNoradId: '43880',
    lookaheadHours: 24,
    minElevation: 10,
    selectedPassIndex: 0,
    passes: [] as any[],
    lastRun: null as any
  },
  eda: {
    noradId: '43880',
    dataLimit: 1000,
    telemetryFrames: [] as any[]
  },
  inspector: {
    noradId: '43880',
    dataLimit: 50,
    telemetryFrames: [] as any[]
  },
  ml: {
    noradId: '43880',
    dataLimit: 50,
    anomalies: [] as any[]
  },
  analytics: {
    activeTab: 'throughput' as 'throughput' | 'quality' | 'health'
  },
  live: {
    noradId: '43880',
    limit: 100,
    isLive: true,
    frames: [] as any[]
  },
  tracker: {
    noradId: '43880',
    activeTab: 'mission' as 'mission' | 'orbital' | 'forecast' | 'conjunctions'
  },
  orbitDecay: {
    noradId: '43880',
    activeTab: 'overview' as 'overview' | 'diagnostics'
  }
});
