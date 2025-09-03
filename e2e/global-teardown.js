/**
 * Playwright Global Teardown
 * Cleans up test environment and generates reports
 */

import fs from 'fs';
import path from 'path';

async function globalTeardown() {
  console.log('🧹 Starting E2E Test Global Teardown...');

  try {
    // Clean up test data
    await cleanupTestData();
    
    // Generate test summary report
    await generateTestSummary();
    
    // Clean up temporary files
    await cleanupTempFiles();
    
    console.log('✅ E2E Test Global Teardown Complete');
  } catch (error) {
    console.error('❌ Error during global teardown:', error);
  }
}

/**
 * Clean up test data
 */
async function cleanupTestData() {
  try {
    // Remove test authentication state
    const authStatePath = path.join(process.cwd(), 'e2e', 'auth-state.json');
    if (fs.existsSync(authStatePath)) {
      fs.unlinkSync(authStatePath);
      console.log('✅ Test authentication state cleaned up');
    }

    // Clean up any test-specific data files
    const testDataPath = path.join(process.cwd(), 'e2e', 'test-data.json');
    if (fs.existsSync(testDataPath)) {
      // Keep test data for debugging if tests failed
      const resultsPath = path.join(process.cwd(), 'e2e-results', 'results.json');
      if (fs.existsSync(resultsPath)) {
        const results = JSON.parse(fs.readFileSync(resultsPath, 'utf8'));
        const hasFailures = results.suites?.some(suite => 
          suite.specs?.some(spec => spec.tests?.some(test => test.status === 'failed'))
        );
        
        if (!hasFailures) {
          fs.unlinkSync(testDataPath);
          console.log('✅ Test data cleaned up');
        } else {
          console.log('ℹ️ Test data preserved for debugging (tests failed)');
        }
      }
    }
  } catch (error) {
    console.warn('⚠️ Error cleaning up test data:', error.message);
  }
}

/**
 * Generate test summary report
 */
async function generateTestSummary() {
  try {
    const resultsPath = path.join(process.cwd(), 'e2e-results', 'results.json');
    
    if (!fs.existsSync(resultsPath)) {
      console.log('ℹ️ No test results found to summarize');
      return;
    }

    const results = JSON.parse(fs.readFileSync(resultsPath, 'utf8'));
    
    // Calculate summary statistics
    let totalTests = 0;
    let passedTests = 0;
    let failedTests = 0;
    let skippedTests = 0;
    let totalDuration = 0;

    results.suites?.forEach(suite => {
      suite.specs?.forEach(spec => {
        spec.tests?.forEach(test => {
          totalTests++;
          totalDuration += test.results?.[0]?.duration || 0;
          
          switch (test.status) {
            case 'passed':
              passedTests++;
              break;
            case 'failed':
              failedTests++;
              break;
            case 'skipped':
              skippedTests++;
              break;
          }
        });
      });
    });

    const summary = {
      timestamp: new Date().toISOString(),
      total: totalTests,
      passed: passedTests,
      failed: failedTests,
      skipped: skippedTests,
      passRate: totalTests > 0 ? ((passedTests / totalTests) * 100).toFixed(2) : 0,
      totalDuration: totalDuration,
      averageDuration: totalTests > 0 ? (totalDuration / totalTests).toFixed(2) : 0,
      status: failedTests === 0 ? 'PASSED' : 'FAILED'
    };

    // Save summary
    const summaryPath = path.join(process.cwd(), 'e2e-results', 'summary.json');
    fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));

    // Generate markdown report
    const markdownReport = generateMarkdownReport(summary, results);
    const reportPath = path.join(process.cwd(), 'e2e-results', 'REPORT.md');
    fs.writeFileSync(reportPath, markdownReport);

    console.log('✅ Test summary generated');
    console.log(`📊 Results: ${passedTests}/${totalTests} passed (${summary.passRate}%)`);
    
    if (failedTests > 0) {
      console.log(`❌ ${failedTests} test(s) failed`);
    }
  } catch (error) {
    console.warn('⚠️ Error generating test summary:', error.message);
  }
}

/**
 * Generate markdown test report
 */
function generateMarkdownReport(summary, results) {
  const timestamp = new Date().toLocaleString();
  
  let report = `# E2E Test Report\n\n`;
  report += `**Generated:** ${timestamp}\n\n`;
  report += `## Summary\n\n`;
  report += `| Metric | Value |\n`;
  report += `|--------|-------|\n`;
  report += `| Total Tests | ${summary.total} |\n`;
  report += `| Passed | ${summary.passed} |\n`;
  report += `| Failed | ${summary.failed} |\n`;
  report += `| Skipped | ${summary.skipped} |\n`;
  report += `| Pass Rate | ${summary.passRate}% |\n`;
  report += `| Total Duration | ${(summary.totalDuration / 1000).toFixed(2)}s |\n`;
  report += `| Average Duration | ${(summary.averageDuration / 1000).toFixed(2)}s |\n`;
  report += `| Status | ${summary.status} |\n\n`;

  // Add failed tests details if any
  if (summary.failed > 0) {
    report += `## Failed Tests\n\n`;
    
    results.suites?.forEach(suite => {
      suite.specs?.forEach(spec => {
        spec.tests?.forEach(test => {
          if (test.status === 'failed') {
            report += `### ${test.title}\n\n`;
            report += `**File:** ${spec.file}\n\n`;
            
            if (test.results?.[0]?.error) {
              report += `**Error:**\n\`\`\`\n${test.results[0].error.message}\n\`\`\`\n\n`;
            }
            
            if (test.results?.[0]?.attachments) {
              report += `**Attachments:**\n`;
              test.results[0].attachments.forEach(attachment => {
                report += `- [${attachment.name}](${attachment.path})\n`;
              });
              report += `\n`;
            }
          }
        });
      });
    });
  }

  // Add test suite breakdown
  report += `## Test Suites\n\n`;
  
  results.suites?.forEach(suite => {
    const suitePassed = suite.specs?.reduce((acc, spec) => {
      return acc + (spec.tests?.filter(test => test.status === 'passed').length || 0);
    }, 0) || 0;
    
    const suiteTotal = suite.specs?.reduce((acc, spec) => {
      return acc + (spec.tests?.length || 0);
    }, 0) || 0;
    
    const suitePassRate = suiteTotal > 0 ? ((suitePassed / suiteTotal) * 100).toFixed(2) : 0;
    
    report += `### ${suite.title}\n\n`;
    report += `- **Tests:** ${suitePassed}/${suiteTotal} passed (${suitePassRate}%)\n`;
    report += `- **File:** ${suite.file}\n\n`;
  });

  return report;
}

/**
 * Clean up temporary files
 */
async function cleanupTempFiles() {
  try {
    // Clean up any temporary screenshots or videos from successful tests
    const artifactsDir = path.join(process.cwd(), 'e2e-results', 'test-artifacts');
    
    if (fs.existsSync(artifactsDir)) {
      const files = fs.readdirSync(artifactsDir);
      let cleanedCount = 0;
      
      files.forEach(file => {
        const filePath = path.join(artifactsDir, file);
        const stats = fs.statSync(filePath);
        
        // Remove files older than 1 hour (for successful test runs)
        if (Date.now() - stats.mtime.getTime() > 60 * 60 * 1000) {
          try {
            fs.unlinkSync(filePath);
            cleanedCount++;
          } catch (error) {
            // Ignore cleanup errors
          }
        }
      });
      
      if (cleanedCount > 0) {
        console.log(`✅ Cleaned up ${cleanedCount} temporary file(s)`);
      }
    }
  } catch (error) {
    console.warn('⚠️ Error cleaning up temporary files:', error.message);
  }
}

export default globalTeardown;
