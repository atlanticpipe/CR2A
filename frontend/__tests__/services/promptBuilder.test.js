/**
 * Tests for Prompt Builder Service
 * Requirements: 13.4 - Unit tests for promptBuilder service covering prompt construction and template handling
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Import PromptBuilder
const PromptBuilder = (await import('../../services/promptBuilder.js')).default;

describe('PromptBuilder Service', () => {
  let builder;

  beforeEach(() => {
    builder = new PromptBuilder();
  });

  describe('Initialization', () => {
    it('should initialize with default prompts', () => {
      expect(builder.prompts).toBeDefined();
      expect(Object.keys(builder.prompts).length).toBeGreaterThan(0);
    });

    it('should have prompts for all required sections', () => {
      const requiredSections = ['section_i', 'section_ii', 'section_iii', 'section_iv', 'section_v', 'section_vi', 'section_vii'];
      
      requiredSections.forEach(section => {
        expect(builder.prompts[section]).toBeDefined();
      });
    });

    it('should not have section_viii (removed per requirements)', () => {
      expect(builder.prompts.section_viii).toBeUndefined();
    });

    it('should initialize with null custom prompts', () => {
      expect(builder.customPrompts).toBeNull();
    });
  });

  describe('Default Prompts Structure', () => {
    it('should have required properties for each section', () => {
      const sections = Object.keys(builder.prompts);
      
      sections.forEach(sectionKey => {
        const section = builder.prompts[sectionKey];
        expect(section).toHaveProperty('name');
        expect(section).toHaveProperty('description');
        expect(section).toHaveProperty('instructions');
      });
    });

    it('should have items array for analysis sections', () => {
      const analysisSections = ['section_ii', 'section_iii', 'section_iv', 'section_v', 'section_vi', 'section_vii'];
      
      analysisSections.forEach(sectionKey => {
        const section = builder.prompts[sectionKey];
        expect(Array.isArray(section.items)).toBe(true);
        expect(section.items.length).toBeGreaterThan(0);
      });
    });

    it('should have properly formatted items', () => {
      const section = builder.prompts.section_ii;
      
      section.items.forEach(item => {
        expect(item).toHaveProperty('name');
        expect(item).toHaveProperty('description');
        expect(typeof item.name).toBe('string');
        expect(typeof item.description).toBe('string');
      });
    });
  });

  describe('Section Prompt Building', () => {
    it('should build prompt for section II', () => {
      const contractText = 'Sample contract text';
      const metadata = {
        contract_id: 'TEST-001',
        project_title: 'Test Project',
        owner: 'Test Owner'
      };

      const prompt = builder.buildSectionPrompt('section_ii', contractText, metadata);

      expect(prompt).toContain(contractText);
      expect(prompt).toContain('TEST-001');
      expect(prompt).toContain('Test Project');
      expect(prompt).toContain('Administrative & Commercial');
    });

    it('should include section instructions', () => {
      const prompt = builder.buildSectionPrompt('section_iii', 'contract text', {});

      expect(prompt).toContain('INSTRUCTIONS');
      expect(prompt).toContain('Technical');
    });

    it('should include items to analyze', () => {
      const prompt = builder.buildSectionPrompt('section_iv', 'contract text', {});

      expect(prompt).toContain('ITEMS TO ANALYZE');
      const section = builder.prompts.section_iv;
      section.items.forEach(item => {
        expect(prompt).toContain(item.name);
      });
    });

    it('should return null for section I (auto-generated)', () => {
      const prompt = builder.buildSectionPrompt('section_i', 'contract text', {});
      expect(prompt).toBeNull();
    });

    it('should throw error for unknown section', () => {
      expect(() => {
        builder.buildSectionPrompt('section_unknown', 'text', {});
      }).toThrow('Unknown section');
    });

    it('should handle empty metadata', () => {
      const prompt = builder.buildSectionPrompt('section_ii', 'contract text', {});
      
      expect(prompt).toBeDefined();
      expect(prompt).toContain('Unknown');
    });

    it('should include output format specification', () => {
      const prompt = builder.buildSectionPrompt('section_v', 'contract text', {});

      expect(prompt).toContain('OUTPUT FORMAT');
    });
  });

  describe('Section Key Management', () => {
    it('should return all section keys except section I', () => {
      const keys = builder.getAllSectionKeys();

      expect(Array.isArray(keys)).toBe(true);
      expect(keys).not.toContain('section_i');
      expect(keys).toContain('section_ii');
      expect(keys).toContain('section_vii');
    });

    it('should not include section VIII', () => {
      const keys = builder.getAllSectionKeys();
      expect(keys).not.toContain('section_viii');
    });

    it('should return exactly 6 sections (II-VII)', () => {
      const keys = builder.getAllSectionKeys();
      expect(keys).toHaveLength(6);
    });
  });

  describe('Section Name Retrieval', () => {
    it('should return section name for valid key', () => {
      const name = builder.getSectionName('section_ii');
      
      expect(name).toBeDefined();
      expect(name).toContain('Administrative');
    });

    it('should return key itself for unknown section', () => {
      const name = builder.getSectionName('section_unknown');
      expect(name).toBe('section_unknown');
    });

    it('should return names for all valid sections', () => {
      const keys = builder.getAllSectionKeys();
      
      keys.forEach(key => {
        const name = builder.getSectionName(key);
        expect(name).toBeDefined();
        expect(name.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Executive Summary Building', () => {
    it('should build executive summary from analysis results', () => {
      const analysisResults = {
        section_ii: {
          findings: [
            { risk_level: 'High' },
            { risk_level: 'Medium' },
            { risk_level: 'Low' }
          ]
        },
        section_iii: {
          findings: [
            { risk_level: 'High' }
          ]
        },
        risk_summary: {
          overallRisk: 'Medium',
          distribution: { High: 2, Medium: 1, Low: 1 }
        }
      };

      const metadata = {
        contract_id: 'TEST-001',
        project_title: 'Test Project'
      };

      const prompt = builder.buildExecutiveSummary(analysisResults, metadata);

      expect(prompt).toContain('executive summary');
      expect(prompt).toContain('TEST-001');
      expect(prompt).toContain('Medium');
    });

    it('should include risk distribution in summary', () => {
      const analysisResults = {
        risk_summary: {
          overallRisk: 'High',
          distribution: { High: 5, Medium: 3, Low: 2 }
        }
      };

      const prompt = builder.buildExecutiveSummary(analysisResults, {});

      // Check for risk numbers in the summary
      expect(prompt).toContain('5');
      expect(prompt).toContain('3');
      expect(prompt).toContain('2');
    });

    it('should include all completed sections', () => {
      const analysisResults = {
        section_ii: { findings: [] },
        section_iii: { findings: [] },
        section_iv: { findings: [] }
      };

      const prompt = builder.buildExecutiveSummary(analysisResults, {});

      // Check for section names (not keys)
      expect(prompt).toContain('Section II');
      expect(prompt).toContain('Section III');
      expect(prompt).toContain('Section IV');
    });

    it('should specify required output format', () => {
      const prompt = builder.buildExecutiveSummary({}, {});

      expect(prompt).toContain('JSON');
      expect(prompt).toContain('overall_assessment');
      expect(prompt).toContain('critical_findings');
      expect(prompt).toContain('key_recommendations');
    });

    it('should handle missing risk summary', () => {
      const analysisResults = {
        section_ii: { findings: [] }
      };

      const prompt = builder.buildExecutiveSummary(analysisResults, {});

      expect(prompt).toBeDefined();
      expect(prompt).toContain('Unknown');
    });
  });

  describe('Custom Prompt Loading', () => {
    it('should load custom prompts from URL', async () => {
      const customPrompts = {
        section_ii: {
          name: 'Custom Section II',
          description: 'Custom description',
          instructions: 'Custom instructions',
          items: []
        }
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => customPrompts
      });

      const result = await builder.loadPromptData('http://example.com/prompts.json');

      expect(result).toBe(true);
      expect(builder.customPrompts).toEqual(customPrompts);
    });

    it('should return false on load failure', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      const result = await builder.loadPromptData('http://example.com/prompts.json');

      expect(result).toBe(false);
      expect(builder.customPrompts).toBeNull();
    });

    it('should use custom prompts after loading', async () => {
      const customPrompts = {
        section_ii: {
          name: 'Custom Section',
          description: 'Custom',
          instructions: 'Custom instructions',
          items: [{ name: 'Custom Item', description: 'Custom' }]
        }
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => customPrompts
      });

      await builder.loadPromptData('http://example.com/prompts.json');

      const prompt = builder.buildSectionPrompt('section_ii', 'contract', {});
      expect(prompt).toContain('Custom Section');
      expect(prompt).toContain('Custom Item');
    });

    it('should handle non-ok response', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404
      });

      const result = await builder.loadPromptData('http://example.com/prompts.json');

      expect(result).toBe(false);
    });
  });

  describe('Prompt Content Validation', () => {
    it('should include contract analysis context', () => {
      const prompt = builder.buildSectionPrompt('section_ii', 'contract text', {});

      expect(prompt).toContain('contract');
      expect(prompt).toContain('risk');
      expect(prompt).toContain('analysis');
    });

    it('should structure prompt with clear sections', () => {
      const prompt = builder.buildSectionPrompt('section_iii', 'contract text', {});

      expect(prompt).toContain('CONTRACT METADATA');
      expect(prompt).toContain('ANALYSIS SECTION');
      expect(prompt).toContain('CONTRACT TEXT');
    });

    it('should include all metadata fields', () => {
      const metadata = {
        contract_id: 'ID-123',
        project_title: 'Project X',
        owner: 'Owner Y',
        custom_field: 'Custom Value'
      };

      const prompt = builder.buildSectionPrompt('section_ii', 'text', metadata);

      expect(prompt).toContain('ID-123');
      expect(prompt).toContain('Project X');
      expect(prompt).toContain('Owner Y');
    });
  });
});
