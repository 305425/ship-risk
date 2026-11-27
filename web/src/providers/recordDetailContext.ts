import { createContext, useContext } from "react";

export const RecordDetailContext = createContext<(id: string) => void>(() => {});

export function useRecordDetail() {
  return useContext(RecordDetailContext);
}
