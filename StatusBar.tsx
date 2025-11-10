import React from 'react';
import { WorkflowStatus } from '../types';
import { CheckIcon } from './icons';

interface StatusBarProps {
  currentStatus: WorkflowStatus;
}

const steps = [
  { id: 1, name: 'Upload Document', statuses: [WorkflowStatus.IDLE, WorkflowStatus.FILE_SELECTED] },
  { id: 2, name: 'AI Processing & Approval', statuses: [WorkflowStatus.PROCESSING, WorkflowStatus.AWAITING_APPROVAL] },
  { id: 3, name: 'Generate & Download', statuses: [WorkflowStatus.FINALIZING, WorkflowStatus.COMPLETED] },
];

const getStepState = (stepStatuses: WorkflowStatus[], currentStatus: WorkflowStatus) => {
  const stepIndex = steps.findIndex(s => s.statuses.includes(currentStatus));
  const currentStepDefIndex = steps.findIndex(s => s.statuses === stepStatuses);

  if (currentStepDefIndex < stepIndex) {
    return 'completed';
  }
  if (currentStepDefIndex === stepIndex) {
    return 'current';
  }
  return 'upcoming';
};

const StatusBar: React.FC<StatusBarProps> = ({ currentStatus }) => {
  return (
    <nav aria-label="Progress">
      <ol role="list" className="flex items-center">
        {steps.map((step, stepIdx) => {
          const state = getStepState(step.statuses, currentStatus);
          const isLastStep = stepIdx === steps.length - 1;

          return (
            <li key={step.name} className={`relative ${!isLastStep ? 'pr-8 sm:pr-20' : ''}`}>
              {state === 'completed' ? (
                <>
                  <div className="absolute inset-0 flex items-center" aria-hidden="true">
                    {!isLastStep && <div className="h-0.5 w-full bg-indigo-600" />}
                  </div>
                  <span className="relative flex h-8 w-8 items-center justify-center bg-indigo-600 rounded-full hover:bg-indigo-700">
                    <CheckIcon className="h-5 w-5 text-white" />
                    <span className="sr-only">{step.name}</span>
                  </span>
                </>
              ) : state === 'current' ? (
                <>
                  <div className="absolute inset-0 flex items-center" aria-hidden="true">
                    {!isLastStep && <div className="h-0.5 w-full bg-gray-700" />}
                  </div>
                  <span className="relative flex h-8 w-8 items-center justify-center bg-indigo-600 rounded-full border-2 border-indigo-600" aria-current="step">
                    <span className="h-2.5 w-2.5 bg-white rounded-full" />
                    <span className="sr-only">{step.name}</span>
                  </span>
                </>
              ) : (
                <>
                  <div className="absolute inset-0 flex items-center" aria-hidden="true">
                    {!isLastStep && <div className="h-0.5 w-full bg-gray-700" />}
                  </div>
                  <span className="relative flex h-8 w-8 items-center justify-center bg-gray-800 rounded-full border-2 border-gray-700 hover:border-gray-500">
                    <span className="h-2.5 w-2.5 bg-transparent rounded-full" />
                    <span className="sr-only">{step.name}</span>
                  </span>
                </>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

export default StatusBar;