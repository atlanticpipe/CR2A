/**
 * Tests for PDF Exporter Service
 * Requirements: 13.3 - Unit tests for pdfExporter service covering PDF generation and formatting
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { sampleAnalysisResponse, samplePDFConfig } from '../fixtures.js';

// Import PDFExporter
const PDFExporter = (await import('../../services/pdfExporter.js')).default;

describe('PDFExporter Service', () => {
  let exporter;

  beforeEach(() => {
    exporter = new PDFExporter();
    
    // Mock jsPDF
    global.window = {
      jspdf: {
        jsPDF: class MockJsPDF {
          constructor() {
            this.pages = 1;
            this.content = [];
          }
          setFontSize(size) { this.fontSize = size; }
          setFont(name, style) { this.font = { name, style }; }
          setTextColor(...color) { this.textColor = color; }
          setFillColor(...color) { this.fillColor = color; }
          setDrawColor(...color) { this.drawColor = color; }
          setLineWidth(width) { this.lineWidth = width; }
          text(text, x, y) { this.content.push({ type: 'text', text, x, y }); }
          rect(x, y, w, h, style) { this.content.push({ type: 'rect', x, y, w, h, style }); }
          line(x1, y1, x2, y2) { this.content.push({ type: 'line', x1, y1, x2, y2 }); }
          addPage() { this.pages++; }
          setPage(num) { this.currentPage = num; }
          getTextWidth(text) { return text.length * 2; }
          save(filename) { this.savedAs = filename; }
          output(type) { return new Blob(['mock pdf'], { type: 'application/pdf' }); }
          internal = {
            getNumberOfPages: () => this.pages
          };
        }
      }
    };
  });

  describe('Initialization', () => {
    it('should initialize with default settings', () => {
      expect(exporter.pageWidth).toBe(210);
      expect(exporter.pageHeight).toBe(297);
      expect(exporter.margin).toBeGreaterThan(0);
      expect(exporter.colors).toBeDefined();
    });

    it('should have color definitions for risk levels', () => {
      expect(exporter.colors.danger).toBeDefined();
      expect(exporter.colors.warning).toBeDefined();
      expect(exporter.colors.success).toBeDefined();
    });
  });

  describe('Risk Color Mapping', () => {
    it('should return correct color for high risk', () => {
      const color = exporter.getRiskColor('High');
      expect(color).toEqual(exporter.colors.danger);
    });

    it('should return correct color for medium risk', () => {
      const color = exporter.getRiskColor('Medium');
      expect(color).toEqual(exporter.colors.warning);
    });

    it('should return correct color for low risk', () => {
      const color = exporter.getRiskColor('Low');
      expect(color).toEqual(exporter.colors.success);
    });

    it('should return gray for unknown risk level', () => {
      const color = exporter.getRiskColor('Unknown');
      expect(color).toEqual(exporter.colors.gray);
    });

    it('should handle case-insensitive risk levels', () => {
      expect(exporter.getRiskColor('high')).toEqual(exporter.colors.danger);
      expect(exporter.getRiskColor('HIGH')).toEqual(exporter.colors.danger);
    });
  });

  describe('Text Wrapping', () => {
    it('should wrap text to fit within width', () => {
      exporter.doc = new window.jspdf.jsPDF();
      
      const longText = 'This is a very long text that should be wrapped into multiple lines';
      const lines = exporter.wrapText(longText, 50);

      expect(Array.isArray(lines)).toBe(true);
      expect(lines.length).toBeGreaterThan(1);
      lines.forEach(line => {
        expect(exporter.doc.getTextWidth(line)).toBeLessThanOrEqual(50);
      });
    });

    it('should handle short text without wrapping', () => {
      exporter.doc = new window.jspdf.jsPDF();
      
      const shortText = 'Short';
      const lines = exporter.wrapText(shortText, 100);

      expect(lines).toHaveLength(1);
      expect(lines[0]).toBe(shortText);
    });

    it('should handle empty text', () => {
      exporter.doc = new window.jspdf.jsPDF();
      
      const lines = exporter.wrapText('', 100);
      // Empty text returns empty array
      expect(Array.isArray(lines)).toBe(true);
    });
  });

  describe('Report Generation', () => {
    it('should generate report with all required sections', async () => {
      const results = {
        executive_summary: {
          overall_assessment: 'Test assessment',
          critical_findings: ['Finding 1', 'Finding 2'],
          key_recommendations: ['Rec 1', 'Rec 2']
        },
        risk_summary: {
          overallRisk: 'Medium',
          totalFindings: 10,
          distribution: { High: 2, Medium: 5, Low: 3 }
        },
        sections: {
          section_ii: {
            findings: [
              {
                item_name: 'Payment Terms',
                risk_level: 'Low',
                status: 'Present',
                details: 'Standard terms',
                recommendations: 'None'
              }
            ]
          }
        }
      };

      const metadata = {
        contract_id: 'TEST-001',
        project_title: 'Test Project'
      };

      const doc = await exporter.generateReport(results, metadata);

      expect(doc).toBeDefined();
      expect(exporter.doc).toBeDefined();
    });

    it('should handle missing sections gracefully', async () => {
      const results = {
        risk_summary: {
          overallRisk: 'Low',
          totalFindings: 0,
          distribution: { High: 0, Medium: 0, Low: 0 }
        },
        sections: {}
      };

      const doc = await exporter.generateReport(results, {});
      expect(doc).toBeDefined();
    });

    it('should throw error on generation failure', async () => {
      // Force an error by not setting up jsPDF
      global.window = undefined;
      
      const results = { risk_summary: {}, sections: {} };
      
      await expect(
        exporter.generateReport(results, {})
      ).rejects.toThrow();
    });
  });

  describe('Cover Page', () => {
    it('should add cover page with metadata', () => {
      exporter.doc = new window.jspdf.jsPDF();
      
      const metadata = {
        contract_id: 'TEST-001',
        project_title: 'Test Project',
        owner: 'Test Owner'
      };

      const riskSummary = {
        overallRisk: 'High',
        totalFindings: 15
      };

      exporter.addCoverPage(metadata, riskSummary);

      expect(exporter.doc.content.length).toBeGreaterThan(0);
      const textContent = exporter.doc.content
        .filter(item => item.type === 'text')
        .map(item => item.text);
      
      expect(textContent.some(text => text.includes('TEST-001'))).toBe(true);
    });
  });

  describe('Section Analysis', () => {
    it('should add section analysis with findings', () => {
      exporter.doc = new window.jspdf.jsPDF();
      
      const sectionData = {
        findings: [
          {
            item_name: 'Test Item',
            risk_level: 'High',
            status: 'Missing',
            details: 'Test details',
            recommendations: 'Test recommendations'
          }
        ]
      };

      exporter.addSectionAnalysis('section_ii', sectionData);

      expect(exporter.doc.content.length).toBeGreaterThan(0);
    });

    it('should handle section with no findings', () => {
      exporter.doc = new window.jspdf.jsPDF();
      
      const sectionData = { findings: [] };

      exporter.addSectionAnalysis('section_ii', sectionData);

      const textContent = exporter.doc.content
        .filter(item => item.type === 'text')
        .map(item => item.text);
      
      expect(textContent.some(text => text.includes('No findings'))).toBe(true);
    });
  });

  describe('Executive Summary', () => {
    it('should add executive summary section', () => {
      exporter.doc = new window.jspdf.jsPDF();
      
      const executiveSummary = {
        overall_assessment: 'Test assessment',
        critical_findings: ['Finding 1', 'Finding 2'],
        key_recommendations: ['Rec 1', 'Rec 2']
      };

      const riskSummary = {
        distribution: { High: 2, Medium: 5, Low: 3 }
      };

      exporter.addExecutiveSummary(executiveSummary, riskSummary);

      expect(exporter.doc.content.length).toBeGreaterThan(0);
    });

    it('should handle missing executive summary data', () => {
      exporter.doc = new window.jspdf.jsPDF();
      
      exporter.addExecutiveSummary({}, {});

      expect(exporter.doc.content.length).toBeGreaterThan(0);
    });
  });

  describe('Risk Dashboard', () => {
    it('should add risk dashboard with statistics', () => {
      exporter.doc = new window.jspdf.jsPDF();
      
      const riskSummary = {
        overallRisk: 'Medium',
        totalFindings: 10,
        distribution: { High: 2, Medium: 5, Low: 3 }
      };

      const sections = {
        section_ii: {
          findings: [
            { risk_level: 'High' },
            { risk_level: 'Medium' }
          ]
        }
      };

      exporter.addRiskDashboard(riskSummary, sections);

      expect(exporter.doc.content.length).toBeGreaterThan(0);
    });
  });

  describe('PDF Output', () => {
    it('should save PDF with filename', () => {
      exporter.doc = new window.jspdf.jsPDF();
      
      exporter.save('test-report.pdf');
      
      expect(exporter.doc.savedAs).toBe('test-report.pdf');
    });

    it('should use default filename if none provided', () => {
      exporter.doc = new window.jspdf.jsPDF();
      
      exporter.save();
      
      expect(exporter.doc.savedAs).toBeDefined();
    });

    it('should get PDF as blob', () => {
      exporter.doc = new window.jspdf.jsPDF();
      
      const blob = exporter.getBlob();
      
      expect(blob).toBeInstanceOf(Blob);
    });

    it('should throw error when getting blob without document', () => {
      expect(() => exporter.getBlob()).toThrow('No document available');
    });

    it('should throw error when saving without document', () => {
      expect(() => exporter.save()).toThrow('No document to save');
    });
  });

  describe('Page Management', () => {
    it('should add new pages', () => {
      exporter.doc = new window.jspdf.jsPDF();
      const initialPages = exporter.doc.pages;
      
      exporter.addNewPage();
      
      expect(exporter.doc.pages).toBe(initialPages + 1);
      expect(exporter.currentY).toBe(exporter.margin);
    });

    it('should add footers to all pages', () => {
      exporter.doc = new window.jspdf.jsPDF();
      exporter.doc.addPage();
      exporter.doc.addPage();
      
      const metadata = { contract_id: 'TEST-001' };
      exporter.addFooters(metadata);

      expect(exporter.doc.content.length).toBeGreaterThan(0);
    });
  });
});
