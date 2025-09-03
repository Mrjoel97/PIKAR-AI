/**
 * File Security Service
 * Comprehensive file upload security with virus scanning, content analysis, and secure handling
 */

import { auditService } from './auditService';

// File type configurations
const FILE_TYPE_CONFIGS = {
  images: {
    extensions: ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'],
    mimeTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/svg+xml'],
    maxSize: 10 * 1024 * 1024, // 10MB
    allowedFor: ['avatar', 'content', 'marketing']
  },
  documents: {
    extensions: ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
    mimeTypes: [
      'application/pdf', 
      'application/msword', 
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
      'application/rtf'
    ],
    maxSize: 50 * 1024 * 1024, // 50MB
    allowedFor: ['knowledge', 'training', 'compliance']
  },
  spreadsheets: {
    extensions: ['.csv', '.xls', '.xlsx'],
    mimeTypes: [
      'text/csv',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ],
    maxSize: 25 * 1024 * 1024, // 25MB
    allowedFor: ['data', 'analytics', 'reports']
  },
  audio: {
    extensions: ['.mp3', '.wav', '.m4a', '.ogg'],
    mimeTypes: ['audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/ogg'],
    maxSize: 100 * 1024 * 1024, // 100MB
    allowedFor: ['voice', 'training']
  },
  video: {
    extensions: ['.mp4', '.webm', '.mov', '.avi'],
    mimeTypes: ['video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo'],
    maxSize: 500 * 1024 * 1024, // 500MB
    allowedFor: ['training', 'marketing']
  }
};

// Dangerous file patterns
const DANGEROUS_PATTERNS = {
  executable: /\.(exe|bat|cmd|com|pif|scr|vbs|js|jar|app|deb|rpm)$/i,
  script: /\.(php|asp|aspx|jsp|py|rb|pl|sh|bash)$/i,
  archive: /\.(zip|rar|7z|tar|gz)$/i, // May contain dangerous files
  doubleExtension: /\.[^.]+\.(exe|bat|cmd|com|pif|scr|vbs|js)$/i,
  hiddenExtension: /\s+\.(exe|bat|cmd|com|pif|scr|vbs|js)$/i
};

// Malicious content signatures (simplified - in production use proper antivirus)
const MALICIOUS_SIGNATURES = [
  // Common malware signatures (hex patterns)
  '4d5a', // MZ header (PE executable)
  '504b0304', // ZIP file header (could contain malware)
  '377abcaf271c', // 7-Zip header
  'cafebabe', // Java class file
  '89504e47', // PNG with potential payload
];

class FileSecurityService {
  constructor() {
    this.quarantineFiles = new Map();
    this.scanCache = new Map();
    this.maxCacheSize = 1000;
  }

  /**
   * Comprehensive file security scan
   * @param {File} file - File to scan
   * @param {Object} options - Scan options
   * @returns {Promise<Object>} Scan result
   */
  async scanFile(file, options = {}) {
    const {
      purpose = 'general',
      userId = null,
      skipCache = false,
      deepScan = true
    } = options;

    try {
      // Generate file hash for caching
      const fileHash = await this.generateFileHash(file);
      
      // Check cache first
      if (!skipCache && this.scanCache.has(fileHash)) {
        const cachedResult = this.scanCache.get(fileHash);
        auditService.logData.modification(userId, 'file_scan_cache_hit', fileHash, {});
        return cachedResult;
      }

      // Start comprehensive scan
      const scanResult = {
        fileHash,
        fileName: file.name,
        fileSize: file.size,
        mimeType: file.type,
        purpose,
        scanTimestamp: new Date().toISOString(),
        threats: [],
        warnings: [],
        metadata: {},
        riskScore: 0,
        allowed: false
      };

      // 1. Basic file validation
      const basicValidation = await this.performBasicValidation(file, purpose);
      if (!basicValidation.passed) {
        scanResult.threats.push(...basicValidation.threats);
        scanResult.riskScore += 50;
      }

      // 2. Filename security check
      const filenameCheck = this.checkFilename(file.name);
      if (!filenameCheck.safe) {
        scanResult.threats.push(...filenameCheck.threats);
        scanResult.riskScore += 30;
      }

      // 3. Content-based scanning
      if (deepScan) {
        const contentScan = await this.performContentScan(file);
        scanResult.threats.push(...contentScan.threats);
        scanResult.warnings.push(...contentScan.warnings);
        scanResult.riskScore += contentScan.riskScore;
        scanResult.metadata = { ...scanResult.metadata, ...contentScan.metadata };
      }

      // 4. Virus signature check (simplified)
      const virusScan = await this.performVirusScan(file);
      if (!virusScan.clean) {
        scanResult.threats.push(...virusScan.threats);
        scanResult.riskScore += 100;
      }

      // 5. Determine final result
      scanResult.allowed = scanResult.riskScore < 50 && scanResult.threats.length === 0;

      // Cache result
      this.cacheResult(fileHash, scanResult);

      // Log scan result
      auditService.logData.modification(userId, 'file_security_scan', fileHash, {
        fileName: file.name,
        riskScore: scanResult.riskScore,
        threatsFound: scanResult.threats.length,
        allowed: scanResult.allowed
      });

      // Quarantine if dangerous
      if (!scanResult.allowed) {
        this.quarantineFile(file, scanResult);
      }

      return scanResult;
    } catch (error) {
      auditService.logSystem.error(error, 'file_security_scan');
      return {
        allowed: false,
        error: 'Scan failed',
        riskScore: 100,
        threats: ['Scan error - file rejected for security']
      };
    }
  }

  /**
   * Basic file validation
   * @param {File} file - File to validate
   * @param {string} purpose - File purpose
   * @returns {Object} Validation result
   */
  async performBasicValidation(file, purpose) {
    const threats = [];
    let passed = true;

    // Check file size
    if (file.size === 0) {
      threats.push('Empty file detected');
      passed = false;
    }

    if (file.size > 1024 * 1024 * 1024) { // 1GB absolute max
      threats.push('File size exceeds maximum limit');
      passed = false;
    }

    // Check file type against purpose
    const allowedConfig = this.getConfigForPurpose(purpose);
    if (allowedConfig) {
      const extension = this.getFileExtension(file.name);
      const mimeValid = allowedConfig.mimeTypes.includes(file.type);
      const extensionValid = allowedConfig.extensions.includes(extension);

      if (!mimeValid || !extensionValid) {
        threats.push(`File type not allowed for purpose: ${purpose}`);
        passed = false;
      }

      if (file.size > allowedConfig.maxSize) {
        threats.push(`File size exceeds limit for ${purpose}`);
        passed = false;
      }
    }

    return { passed, threats };
  }

  /**
   * Check filename for security issues
   * @param {string} filename - Filename to check
   * @returns {Object} Check result
   */
  checkFilename(filename) {
    const threats = [];
    let safe = true;

    // Check for dangerous patterns
    for (const [type, pattern] of Object.entries(DANGEROUS_PATTERNS)) {
      if (pattern.test(filename)) {
        threats.push(`Dangerous ${type} pattern detected in filename`);
        safe = false;
      }
    }

    // Check for directory traversal
    if (filename.includes('..') || filename.includes('/') || filename.includes('\\')) {
      threats.push('Directory traversal attempt detected');
      safe = false;
    }

    // Check for null bytes
    if (filename.includes('\0')) {
      threats.push('Null byte injection detected');
      safe = false;
    }

    // Check for excessively long filename
    if (filename.length > 255) {
      threats.push('Filename too long');
      safe = false;
    }

    // Check for reserved names (Windows)
    const reservedNames = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'];
    const baseName = filename.split('.')[0].toUpperCase();
    if (reservedNames.includes(baseName)) {
      threats.push('Reserved filename detected');
      safe = false;
    }

    return { safe, threats };
  }

  /**
   * Perform content-based scanning
   * @param {File} file - File to scan
   * @returns {Promise<Object>} Scan result
   */
  async performContentScan(file) {
    const threats = [];
    const warnings = [];
    const metadata = {};
    let riskScore = 0;

    try {
      // Read file header (first 1KB)
      const headerBuffer = await this.readFileHeader(file, 1024);
      const headerHex = this.bufferToHex(headerBuffer);

      // Check file signature matches extension
      const expectedSignature = this.getExpectedSignature(file.name, file.type);
      if (expectedSignature && !headerHex.startsWith(expectedSignature)) {
        warnings.push('File signature does not match extension');
        riskScore += 20;
      }

      // Check for embedded executables
      if (this.containsExecutableSignatures(headerHex)) {
        threats.push('Embedded executable detected');
        riskScore += 80;
      }

      // Check for suspicious patterns
      const suspiciousPatterns = this.findSuspiciousPatterns(headerHex);
      if (suspiciousPatterns.length > 0) {
        warnings.push(`Suspicious patterns found: ${suspiciousPatterns.join(', ')}`);
        riskScore += suspiciousPatterns.length * 10;
      }

      // Metadata extraction
      metadata.headerSignature = headerHex.substring(0, 16);
      metadata.fileStructure = this.analyzeFileStructure(headerBuffer);

    } catch (error) {
      warnings.push('Content scan partially failed');
      riskScore += 10;
    }

    return { threats, warnings, metadata, riskScore };
  }

  /**
   * Simplified virus scanning (in production, use proper antivirus API)
   * @param {File} file - File to scan
   * @returns {Promise<Object>} Scan result
   */
  async performVirusScan(file) {
    const threats = [];
    let clean = true;

    try {
      // Read file content (first 64KB for signature checking)
      const buffer = await this.readFileHeader(file, 64 * 1024);
      const hex = this.bufferToHex(buffer);

      // Check against known malicious signatures
      for (const signature of MALICIOUS_SIGNATURES) {
        if (hex.includes(signature.toLowerCase())) {
          threats.push(`Malicious signature detected: ${signature}`);
          clean = false;
        }
      }

      // Check for script injection in text files
      if (file.type.startsWith('text/') || file.name.endsWith('.txt')) {
        const text = new TextDecoder().decode(buffer);
        const scriptPatterns = [
          /<script/i,
          /javascript:/i,
          /vbscript:/i,
          /onload=/i,
          /onerror=/i
        ];

        for (const pattern of scriptPatterns) {
          if (pattern.test(text)) {
            threats.push('Script injection detected');
            clean = false;
            break;
          }
        }
      }

    } catch (error) {
      // If we can't scan, err on the side of caution
      threats.push('Virus scan failed - file rejected');
      clean = false;
    }

    return { clean, threats };
  }

  // Utility methods
  async generateFileHash(file) {
    const buffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  async readFileHeader(file, bytes) {
    const slice = file.slice(0, bytes);
    return await slice.arrayBuffer();
  }

  bufferToHex(buffer) {
    return Array.from(new Uint8Array(buffer))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  }

  getFileExtension(filename) {
    return filename.toLowerCase().substring(filename.lastIndexOf('.'));
  }

  getConfigForPurpose(purpose) {
    // Map purposes to file type configs
    const purposeMap = {
      avatar: FILE_TYPE_CONFIGS.images,
      content: FILE_TYPE_CONFIGS.images,
      marketing: FILE_TYPE_CONFIGS.images,
      knowledge: FILE_TYPE_CONFIGS.documents,
      training: FILE_TYPE_CONFIGS.documents,
      compliance: FILE_TYPE_CONFIGS.documents,
      data: FILE_TYPE_CONFIGS.spreadsheets,
      analytics: FILE_TYPE_CONFIGS.spreadsheets,
      reports: FILE_TYPE_CONFIGS.spreadsheets,
      voice: FILE_TYPE_CONFIGS.audio,
      video: FILE_TYPE_CONFIGS.video
    };

    return purposeMap[purpose] || null;
  }

  getExpectedSignature(filename, mimeType) {
    const signatures = {
      'image/jpeg': 'ffd8ff',
      'image/png': '89504e47',
      'image/gif': '474946',
      'application/pdf': '25504446',
      'application/zip': '504b0304'
    };

    return signatures[mimeType];
  }

  containsExecutableSignatures(hex) {
    const executableSignatures = ['4d5a', '7f454c46', 'cafebabe', 'feedface'];
    return executableSignatures.some(sig => hex.includes(sig));
  }

  findSuspiciousPatterns(hex) {
    const patterns = [];
    
    // Check for multiple file signatures (polyglot files)
    const signatures = ['ffd8ff', '89504e47', '474946', '25504446'];
    const foundSignatures = signatures.filter(sig => hex.includes(sig));
    if (foundSignatures.length > 1) {
      patterns.push('polyglot_file');
    }

    return patterns;
  }

  analyzeFileStructure(buffer) {
    // Basic file structure analysis
    const view = new DataView(buffer);
    const structure = {
      hasNullBytes: buffer.byteLength > 0 && new Uint8Array(buffer).includes(0),
      entropy: this.calculateEntropy(new Uint8Array(buffer)),
      suspiciousHeaders: false
    };

    return structure;
  }

  calculateEntropy(data) {
    const frequency = new Array(256).fill(0);
    for (let i = 0; i < data.length; i++) {
      frequency[data[i]]++;
    }

    let entropy = 0;
    for (let i = 0; i < 256; i++) {
      if (frequency[i] > 0) {
        const p = frequency[i] / data.length;
        entropy -= p * Math.log2(p);
      }
    }

    return entropy;
  }

  cacheResult(fileHash, result) {
    if (this.scanCache.size >= this.maxCacheSize) {
      const firstKey = this.scanCache.keys().next().value;
      this.scanCache.delete(firstKey);
    }
    this.scanCache.set(fileHash, result);
  }

  quarantineFile(file, scanResult) {
    this.quarantineFiles.set(scanResult.fileHash, {
      file,
      scanResult,
      quarantineTime: new Date().toISOString()
    });
  }

  /**
   * Get quarantined files (admin only)
   * @returns {Array} Quarantined files
   */
  getQuarantinedFiles() {
    return Array.from(this.quarantineFiles.values());
  }

  /**
   * Clear quarantine (admin only)
   */
  clearQuarantine() {
    this.quarantineFiles.clear();
  }
}

// Create and export singleton instance
export const fileSecurityService = new FileSecurityService();
