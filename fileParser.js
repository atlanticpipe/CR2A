// File Parser Service - Client-side document parsing
// Replaces AWS S3 + Lambda file processing

class FileParser {
  constructor() {
    this.supportedTypes = ['pdf', 'docx', 'txt'];
    this.maxFileSizeMB = 500;
  }

  /**
   * Parse file based on type
   * @param {File} file - File object from input
   * @returns {Promise<object>} Parsed content and metadata
   */
  async parseFile(file) {
    // Validate file
    this.validateFile(file);

    const extension = this.getFileExtension(file.name);
    const metadata = this.extractMetadata(file);

    let content = '';

    switch (extension) {
      case 'pdf':
        content = await this.parsePDF(file);
        break;
      case 'docx':
        content = await this.parseDOCX(file);
        break;
      case 'txt':
        content = await this.parseTXT(file);
        break;
      default:
        throw new Error(`Unsupported file type: ${extension}`);
    }

    return {
      content: this.cleanText(content),
      metadata,
      wordCount: this.countWords(content),
      characterCount: content.length
    };
  }

  /**
   * Parse PDF using PDF.js
   */
  async parsePDF(file) {
    if (typeof pdfjsLib === 'undefined') {
      throw new Error('PDF.js library not loaded. Include it in your HTML.');
    }

    try {
      const arrayBuffer = await file.arrayBuffer();

      // Configure PDF.js worker
      pdfjsLib.GlobalWorkerOptions.workerSrc = 
        'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

      const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
      const pdf = await loadingTask.promise;

      let fullText = '';
      const pageCount = pdf.numPages;

      // Extract text from each page
      for (let i = 1; i <= pageCount; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();

        // Combine text items with proper spacing
        const pageText = textContent.items
          .map(item => item.str)
          .join(' ');

        fullText += `\n\n--- Page ${i} ---\n\n${pageText}`;
      }

      return fullText;

    } catch (error) {
      console.error('PDF parsing error:', error);
      throw new Error(`Failed to parse PDF: ${error.message}`);
    }
  }

  /**
   * Parse DOCX using Mammoth.js
   */
  async parseDOCX(file) {
    if (typeof mammoth === 'undefined') {
      throw new Error('Mammoth.js library not loaded. Include it in your HTML.');
    }

    try {
      const arrayBuffer = await file.arrayBuffer();

      // Extract raw text
      const result = await mammoth.extractRawText({ arrayBuffer });

      if (result.messages.length > 0) {
        console.warn('DOCX parsing warnings:', result.messages);
      }

      return result.value;

    } catch (error) {
      console.error('DOCX parsing error:', error);
      throw new Error(`Failed to parse DOCX: ${error.message}`);
    }
  }

  /**
   * Parse plain text file
   */
  async parseTXT(file) {
    try {
      return await file.text();
    } catch (error) {
      console.error('TXT parsing error:', error);
      throw new Error(`Failed to parse text file: ${error.message}`);
    }
  }

  /**
   * Validate file before parsing
   */
  validateFile(file) {
    if (!file) {
      throw new Error('No file provided');
    }

    // Check file size
    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > this.maxFileSizeMB) {
      throw new Error(
        `File too large: ${sizeMB.toFixed(2)} MB (max: ${this.maxFileSizeMB} MB)`
      );
    }

    // Check file type
    const extension = this.getFileExtension(file.name);
    if (!this.supportedTypes.includes(extension)) {
      throw new Error(
        `Unsupported file type: ${extension}. Supported: ${this.supportedTypes.join(', ')}`
      );
    }

    return true;
  }

  /**
   * Extract metadata from file
   */
  extractMetadata(file) {
    return {
      filename: file.name,
      size: file.size,
      sizeFormatted: this.formatFileSize(file.size),
      type: file.type,
      extension: this.getFileExtension(file.name),
      lastModified: new Date(file.lastModified).toISOString(),
      uploadedAt: new Date().toISOString()
    };
  }

  /**
   * Get file extension
   */
  getFileExtension(filename) {
    return filename.split('.').pop().toLowerCase();
  }

  /**
   * Format file size for display
   */
  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }

  /**
   * Clean and normalize extracted text
   */
  cleanText(text) {
    return text
      // Remove excessive whitespace
      .replace(/\s+/g, ' ')
      // Remove control characters
      .replace(/[\x00-\x1F\x7F]/g, '')
      // Normalize line breaks
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      // Remove excessive line breaks
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }

  /**
   * Count words in text
   */
  countWords(text) {
    return text
      .trim()
      .split(/\s+/)
      .filter(word => word.length > 0)
      .length;
  }

  /**
   * Split text into chunks for processing
   * @param {string} text - Text to split
   * @param {number} maxChunkSize - Maximum characters per chunk
   * @returns {Array<string>} Array of text chunks
   */
  splitIntoChunks(text, maxChunkSize = 8000) {
    const chunks = [];
    const paragraphs = text.split(/\n\n+/);

    let currentChunk = '';

    for (const paragraph of paragraphs) {
      if ((currentChunk + paragraph).length > maxChunkSize) {
        if (currentChunk) {
          chunks.push(currentChunk.trim());
          currentChunk = '';
        }

        // If single paragraph exceeds max size, split by sentences
        if (paragraph.length > maxChunkSize) {
          const sentences = paragraph.match(/[^.!?]+[.!?]+/g) || [paragraph];
          for (const sentence of sentences) {
            if ((currentChunk + sentence).length > maxChunkSize) {
              if (currentChunk) chunks.push(currentChunk.trim());
              currentChunk = sentence;
            } else {
              currentChunk += sentence;
            }
          }
        } else {
          currentChunk = paragraph;
        }
      } else {
        currentChunk += (currentChunk ? '\n\n' : '') + paragraph;
      }
    }

    if (currentChunk) {
      chunks.push(currentChunk.trim());
    }

    return chunks;
  }

  /**
   * Extract contract sections if they're labeled
   */
  detectSections(text) {
    const sections = {};
    const sectionRegex = /(?:^|\n)\s*(Section|Article|Chapter)\s+([IVXLCDM]+|\d+)[:.\s]+([^\n]+)/gi;

    let match;
    while ((match = sectionRegex.exec(text)) !== null) {
      const sectionType = match[1];
      const sectionNumber = match[2];
      const sectionTitle = match[3].trim();
      const key = `${sectionType} ${sectionNumber}`;

      sections[key] = {
        number: sectionNumber,
        title: sectionTitle,
        index: match.index
      };
    }

    return sections;
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = FileParser;
}
