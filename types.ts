import { jsPDF } from 'jspdf';

export enum WorkflowStatus {
  IDLE = 'IDLE',
  FILE_SELECTED = 'FILE_SELECTED',
  PROCESSING = 'PROCESSING',
  AWAITING_APPROVAL = 'AWAITING_APPROVAL',
  FINALIZING = 'FINALIZING',
  COMPLETED = 'COMPLETED',
  ERROR = 'ERROR',
}

export interface ApprovalData {
  summary: string;
  takeaway: string;
}

declare global {
  interface Window {
    jspdf: {
      jsPDF: typeof jsPDF;
    };
  }
}