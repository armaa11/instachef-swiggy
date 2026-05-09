import { create } from 'zustand'

export type ScreenState = "input" | "progress" | "review" | "tracking";

export interface AppState {
  session_id: string;
  screen: ScreenState;
  pipeline_events: any[];
  cart_proposal: any;
  order_id: string | null;
  setSessionId: (id: string) => void;
  setScreen: (screen: ScreenState) => void;
  addEvent: (event: any) => void;
  setCartProposal: (proposal: any) => void;
  setOrderId: (id: string) => void;
  reset: () => void;
}

export const useStore = create<AppState>((set) => ({
  session_id: "",
  screen: "input",
  pipeline_events: [],
  cart_proposal: null,
  order_id: null,
  setSessionId: (id) => set({ session_id: id }),
  setScreen: (screen) => set({ screen }),
  addEvent: (event) => set((state) => ({ pipeline_events: [...state.pipeline_events, event] })),
  setCartProposal: (proposal) => set({ cart_proposal: proposal }),
  setOrderId: (id) => set({ order_id: id }),
  reset: () => set({ screen: "input", pipeline_events: [], cart_proposal: null, order_id: null }),
}))
