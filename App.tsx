import React, { useState, useCallback } from 'react';
import { GoogleGenAI, Type } from '@google/genai';
import { WorkflowStatus, ApprovalData } from './types';
import StatusBar from './components/StatusBar';
import { UploadIcon, CheckIcon, XIcon, DownloadIcon, Spinner } from './components/icons';

// --- Helper Functions ---
const readFileAsText = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = (error) => reject(error);
    reader.readAsText(file);
  });
};

// --- UI Sub-components defined outside the main App component ---

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  onStart: () => void;
  file: File | null;
  isProcessing: boolean;
  status: WorkflowStatus;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileSelect, onStart, file, isProcessing, status }) => {
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      onFileSelect(event.target.files[0]);
    }
  };

  return (
    <div className="w-full max-w-lg text-center">
      <h2 className="text-2xl font-bold mb-4 text-indigo-300">Step 1: Upload Document</h2>
      <p className="text-gray-400 mb-6">Select a document file (.txt, .md) to begin the AI workflow.</p>
      <label htmlFor="file-upload" className="relative cursor-pointer bg-gray-800 rounded-md font-medium text-indigo-400 hover:text-indigo-300 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-offset-gray-900 focus-within:ring-indigo-500">
        <div className="flex justify-center items-center border-2 border-dashed border-gray-600 rounded-lg p-12 hover:border-indigo-500 transition-colors">
          <div className="space-y-1 text-center">
            <UploadIcon className="mx-auto h-12 w-12 text-gray-500" />
            <div className="flex text-sm text-gray-400">
              <span>{file ? 'Replace file' : 'Upload a file'}</span>
              <input id="file-upload" name="file-upload" type="file" className="sr-only" onChange={handleFileChange} accept=".txt,.md" />
            </div>
            <p className="text-xs text-gray-500">{file ? file.name : 'TXT or MD up to 10MB'}</p>
          </div>
        </div>
      </label>
      {status === WorkflowStatus.FILE_SELECTED && (
        <button
          onClick={onStart}
          disabled={isProcessing}
          className="mt-8 w-full inline-flex justify-center items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900 focus:ring-indigo-500 disabled:bg-indigo-400 disabled:cursor-not-allowed"
        >
          {isProcessing ? <Spinner /> : 'Start Workflow'}
        </button>
      )}
    </div>
  );
};

interface ApprovalStepProps {
  approvalData: ApprovalData;
  onApprove: () => void;
  onReject: () => void;
  isProcessing: boolean;
}

const ApprovalStep: React.FC<ApprovalStepProps> = ({ approvalData, onApprove, onReject, isProcessing }) => (
  <div className="w-full max-w-2xl text-left bg-gray-800 p-8 rounded-lg shadow-xl">
    <h2 className="text-2xl font-bold mb-4 text-indigo-300">Step 2: Awaiting Your Approval</h2>
    <p className="text-gray-400 mb-6">The AI has processed your document. Please review the summary and key takeaway below before proceeding.</p>
    <div className="space-y-4 bg-gray-900 p-6 rounded-md">
      <div>
        <h3 className="font-semibold text-lg text-gray-200">Summary</h3>
        <p className="text-gray-400">{approvalData.summary}</p>
      </div>
      <div>
        <h3 className="font-semibold text-lg text-gray-200">Key Takeaway</h3>
        <p className="text-gray-400 italic">"{approvalData.takeaway}"</p>
      </div>
    </div>
    <div className="mt-8 flex justify-end space-x-4">
      <button
        onClick={onReject}
        disabled={isProcessing}
        className="inline-flex items-center px-4 py-2 border border-gray-600 text-sm font-medium rounded-md text-gray-300 bg-gray-700 hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900 focus:ring-indigo-500 disabled:opacity-50"
      >
        <XIcon className="w-5 h-5 mr-2" /> Reject
      </button>
      <button
        onClick={onApprove}
        disabled={isProcessing}
        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900 focus:ring-green-500 disabled:bg-green-400"
      >
        {isProcessing ? <Spinner className="w-5 h-5 mr-2" /> : <CheckIcon className="w-5 h-5 mr-2" />} Approve & Finalize
      </button>
    </div>
  </div>
);

interface DownloadStepProps {
  pdfUrl: string;
  onReset: () => void;
}

const DownloadStep: React.FC<DownloadStepProps> = ({ pdfUrl, onReset }) => (
  <div className="w-full max-w-lg text-center">
    <h2 className="text-2xl font-bold mb-4 text-green-300">Step 3: Workflow Complete!</h2>
    <p className="text-gray-400 mb-8">Your document has been finalized and converted to a PDF. Download it below.</p>
    <div className="flex flex-col items-center space-y-6">
      <a
        href={pdfUrl}
        download="ai_generated_report.pdf"
        className="w-full inline-flex justify-center items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900 focus:ring-indigo-500"
      >
        <DownloadIcon className="w-5 h-5 mr-2" /> Download PDF
      </a>
      <button
        onClick={onReset}
        className="text-indigo-400 hover:text-indigo-300 text-sm font-medium"
      >
        Start a new workflow
      </button>
    </div>
  </div>
);


// --- Main App Component ---

const App: React.FC = () => {
  const [status, setStatus] = useState<WorkflowStatus>(WorkflowStatus.IDLE);
  const [file, setFile] = useState<File | null>(null);
  const [approvalData, setApprovalData] = useState<ApprovalData | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile);
    setStatus(WorkflowStatus.FILE_SELECTED);
    setError(null);
  };

  const handleStartWorkflow = useCallback(async () => {
    if (!file) return;

    setIsProcessing(true);
    setError(null);
    setStatus(WorkflowStatus.PROCESSING);

    try {
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY as string });
      const documentText = await readFileAsText(file);

      const response = await ai.models.generateContent({
        model: 'gemini-2.5-flash',
        contents: `You are a document analysis expert. Please read the following document content and provide a concise one-paragraph summary and a single, most important key takeaway. The document content is as follows:\n\n---\n\n${documentText}\n\n---\n\nReturn your answer ONLY in the specified JSON format.`,
        config: {
          responseMimeType: 'application/json',
          responseSchema: {
            type: Type.OBJECT,
            properties: {
              summary: { type: Type.STRING, description: 'A one-paragraph summary of the document.' },
              takeaway: { type: Type.STRING, description: 'The single most important key takeaway from the document.' },
            },
            required: ['summary', 'takeaway'],
          },
        },
      });

      const data = JSON.parse(response.text);
      setApprovalData(data);
      setStatus(WorkflowStatus.AWAITING_APPROVAL);
    } catch (err) {
      console.error(err);
      setError('Failed to process the document. Please try again.');
      setStatus(WorkflowStatus.ERROR);
    } finally {
      setIsProcessing(false);
    }
  }, [file]);

  const handleApproval = useCallback(async (approved: boolean) => {
    if (!approvalData) return;

    setIsProcessing(true);
    setError(null);
    setStatus(WorkflowStatus.FINALIZING);

    try {
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY as string });
      const prompt = approved
        ? `An AI-generated summary and takeaway for a document was approved. Based on this information, write a formal, one-page report. Start with the title 'Official Document Report'. The summary was: '${approvalData.summary}'. The key takeaway was: '${approvalData.takeaway}'. Use appropriate spacing and line breaks for a clean report layout.`
        : `An AI-generated summary for a document was rejected by the user. Generate a brief notice stating that the workflow was halted due to user rejection of the initial analysis. Start with the title 'Workflow Process Halted'.`;

      const response = await ai.models.generateContent({
        model: 'gemini-2.5-flash',
        contents: prompt,
      });

      const reportText = response.text;
      
      const { jsPDF } = window.jspdf;
      const doc = new jsPDF();
      doc.text(reportText, 10, 10, { maxWidth: 190 });
      const url = doc.output('bloburl').toString();
      
      setPdfUrl(url);
      setStatus(WorkflowStatus.COMPLETED);

    } catch (err) {
      console.error(err);
      setError('Failed to finalize the report. Please try again.');
      setStatus(WorkflowStatus.ERROR);
    } finally {
      setIsProcessing(false);
    }
  }, [approvalData]);

  const handleReset = () => {
    setStatus(WorkflowStatus.IDLE);
    setFile(null);
    setApprovalData(null);
    setPdfUrl(null);
    setError(null);
    setIsProcessing(false);
  };

  const renderContent = () => {
    switch (status) {
      case WorkflowStatus.IDLE:
      case WorkflowStatus.FILE_SELECTED:
        return <FileUpload onFileSelect={handleFileSelect} onStart={handleStartWorkflow} file={file} isProcessing={isProcessing} status={status} />;
      case WorkflowStatus.PROCESSING:
      case WorkflowStatus.FINALIZING:
        return (
          <div className="text-center">
            <Spinner className="w-12 h-12 mx-auto text-indigo-400" />
            <p className="mt-4 text-lg text-gray-400">{status === WorkflowStatus.PROCESSING ? 'Analyzing document...' : 'Generating final PDF...'}</p>
          </div>
        );
      case WorkflowStatus.AWAITING_APPROVAL:
        return approvalData && <ApprovalStep approvalData={approvalData} onApprove={() => handleApproval(true)} onReject={() => handleApproval(false)} isProcessing={isProcessing} />;
      case WorkflowStatus.COMPLETED:
        return pdfUrl && <DownloadStep pdfUrl={pdfUrl} onReset={handleReset} />;
      case WorkflowStatus.ERROR:
        return (
          <div className="text-center bg-red-900/50 border border-red-700 p-6 rounded-lg">
            <h2 className="text-xl font-bold text-red-300">An Error Occurred</h2>
            <p className="text-red-400 mt-2 mb-4">{error}</p>
            <button onClick={handleReset} className="text-indigo-400 hover:text-indigo-300 text-sm font-medium">
              Start Over
            </button>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="w-full max-w-4xl mx-auto">
        <header className="text-center mb-12">
          <h1 className="text-4xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400 sm:text-5xl">
            AI Document Workflow
          </h1>
          <p className="mt-4 text-xl text-gray-400">Transform your documents into finalized reports with AI assistance.</p>
        </header>

        <div className="mb-12 flex justify-center">
          <StatusBar currentStatus={status} />
        </div>

        <main className="flex justify-center items-center">
          {renderContent()}
        </main>
      </div>
       <footer className="absolute bottom-4 text-center text-gray-600 text-sm">
        <p>Powered by Gemini API. App hosted at ai.velmur.info</p>
      </footer>
    </div>
  );
};

export default App;