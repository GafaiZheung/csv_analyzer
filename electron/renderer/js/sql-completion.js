/**
 * sql-completion.js – Monaco SQL auto-completion provider.
 *
 * Provides:
 *  - SQL keyword completion (dialect-aware)
 *  - Data type completion
 *  - Built-in function completion
 *  - Table name completion (from active connections)
 *  - Column name completion (context-aware)
 *  - Auto alias generation (e.g., user_orders → uo)
 *  - Alias-based column completion (type alias. to get columns)
 *  - SQL snippet completion
 *
 * Dialect files: js/sql-dialects/<dialect>.json
 * Default dialect: mysql. Configurable via SqlCompletion.setDialect().
 */
const SqlCompletion = (() => {

  const SUPPORTED_DIALECTS = ['mysql', 'postgresql', 'duckdb'];
  const DEFAULT_DIALECT = 'mysql';

  let _dialect = DEFAULT_DIALECT;
  let _dialectData = null;
  let _registered = false;

  // Cache for table/column metadata
  const _tableCache = new Map();  // 'connId:schema.table' -> [columns]

  /**
   * Initialize the completion provider. Call after Monaco is ready.
   */
  async function init(dialect) {
    _dialect = dialect || DEFAULT_DIALECT;
    await _loadDialect(_dialect);
    if (!_registered) {
      _registerProvider();
      _registered = true;
    }
  }

  /**
   * Change the active SQL dialect.
   */
  async function setDialect(dialect) {
    if (!SUPPORTED_DIALECTS.includes(dialect)) dialect = DEFAULT_DIALECT;
    if (dialect === _dialect && _dialectData) return;
    _dialect = dialect;
    await _loadDialect(dialect);
  }

  /**
   * Set cached columns for a table (called when columns are loaded).
   */
  function setCachedColumns(connId, schema, table, columns) {
    const key = `${connId}:${schema}.${table}`;
    _tableCache.set(key, columns);
  }

  function getDialect() { return _dialect; }

  // ---- Internal ----

  async function _loadDialect(name) {
    try {
      const resp = await fetch(`js/sql-dialects/${name}.json`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      _dialectData = await resp.json();
    } catch (err) {
      console.error(`Failed to load SQL dialect "${name}":`, err);
      _dialectData = { keywords: [], dataTypes: [], functions: [], snippets: [] };
    }
  }

  function _registerProvider() {
    monaco.languages.registerCompletionItemProvider('sql', {
      triggerCharacters: ['.', ' ', '('],
      provideCompletionItems: (model, position) => {
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        };

        const lineContent = model.getLineContent(position.lineNumber);
        const textBefore = lineContent.substring(0, position.column - 1);
        const fullText = model.getValue();

        const suggestions = [];

        // Check for dot notation (alias.column or schema.table)
        const dotMatch = textBefore.match(/(\w+)\.\s*$/);
        if (dotMatch) {
          const prefix = dotMatch[1];
          _addAliasColumnSuggestions(suggestions, range, prefix, fullText);
          _addSchemaTableSuggestions(suggestions, range, prefix);
          return { suggestions };
        }

        // Keywords
        _addKeywordSuggestions(suggestions, range);

        // Data types
        if (_isTypeContext(textBefore)) {
          _addDataTypeSuggestions(suggestions, range);
        }

        // Functions
        _addFunctionSuggestions(suggestions, range);

        // Table names (after FROM, JOIN, UPDATE, INTO, TABLE, etc.)
        if (_isTableContext(textBefore)) {
          _addTableSuggestions(suggestions, range);
        }

        // Column names
        if (_isColumnContext(textBefore)) {
          _addColumnSuggestions(suggestions, range, fullText);
        }

        // Snippets
        _addSnippetSuggestions(suggestions, range);

        return { suggestions };
      },
    });
  }

  // ---- Context detection ----

  function _isTableContext(textBefore) {
    return /\b(?:FROM|JOIN|UPDATE|INTO|TABLE|DESCRIBE|DESC)\s*$/i.test(textBefore.trimEnd()) ||
           /\b(?:FROM|JOIN)\s+\w+\s*,\s*$/i.test(textBefore.trimEnd());
  }

  function _isColumnContext(textBefore) {
    return /\b(?:SELECT|WHERE|AND|OR|ON|SET|ORDER\s+BY|GROUP\s+BY|HAVING)\s+/i.test(textBefore);
  }

  function _isTypeContext(textBefore) {
    return /CREATE\s+TABLE\b/i.test(textBefore) && /\b\w+\s+$/i.test(textBefore);
  }

  // ---- Suggestion builders ----

  function _addKeywordSuggestions(suggestions, range) {
    if (!_dialectData?.keywords) return;
    for (const kw of _dialectData.keywords) {
      suggestions.push({
        label: kw,
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: kw,
        range,
        sortText: '2_' + kw,
      });
    }
  }

  function _addDataTypeSuggestions(suggestions, range) {
    if (!_dialectData?.dataTypes) return;
    for (const dt of _dialectData.dataTypes) {
      suggestions.push({
        label: dt,
        kind: monaco.languages.CompletionItemKind.TypeParameter,
        insertText: dt,
        range,
        sortText: '3_' + dt,
      });
    }
  }

  function _addFunctionSuggestions(suggestions, range) {
    if (!_dialectData?.functions) return;
    for (const fn of _dialectData.functions) {
      suggestions.push({
        label: fn + '()',
        kind: monaco.languages.CompletionItemKind.Function,
        insertText: fn + '($0)',
        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        detail: _dialectData.name || 'Function',
        range,
        sortText: '4_' + fn,
      });
    }
  }

  function _addTableSuggestions(suggestions, range) {
    const tables = _getAvailableTables();
    for (const t of tables) {
      const alias = _generateAlias(t.name);
      // With auto-generated alias
      suggestions.push({
        label: t.name,
        kind: monaco.languages.CompletionItemKind.Struct,
        insertText: t.name + ' ' + alias,
        detail: `${t.schema} → ${alias}`,
        range,
        sortText: '1_' + t.name,
      });
      // Without alias
      suggestions.push({
        label: `${t.name} (no alias)`,
        kind: monaco.languages.CompletionItemKind.Struct,
        insertText: t.name,
        detail: t.schema,
        range,
        sortText: '1z_' + t.name,
      });
    }
  }

  function _addColumnSuggestions(suggestions, range, fullText) {
    const aliases = _parseAliases(fullText);
    const seen = new Set();

    // Direct column names from all cached tables
    for (const [, columns] of _tableCache) {
      for (const col of columns) {
        if (seen.has(col.name)) continue;
        seen.add(col.name);
        suggestions.push({
          label: col.name,
          kind: monaco.languages.CompletionItemKind.Field,
          insertText: col.name,
          detail: col.data_type || '',
          range,
          sortText: '0_' + col.name,
        });
      }
    }

    // Alias-prefixed columns
    for (const [alias, tableInfo] of aliases) {
      const key = `${tableInfo.connId}:${tableInfo.schema}.${tableInfo.table}`;
      const columns = _tableCache.get(key);
      if (!columns) continue;
      for (const col of columns) {
        const label = `${alias}.${col.name}`;
        if (seen.has(label)) continue;
        seen.add(label);
        suggestions.push({
          label,
          kind: monaco.languages.CompletionItemKind.Field,
          insertText: label,
          detail: `${col.data_type} (${alias})`,
          range,
          sortText: '0a_' + label,
        });
      }
    }
  }

  function _addAliasColumnSuggestions(suggestions, range, alias, fullText) {
    const aliases = _parseAliases(fullText);
    const tableInfo = aliases.get(alias.toLowerCase());

    if (tableInfo) {
      const key = `${tableInfo.connId}:${tableInfo.schema}.${tableInfo.table}`;
      const columns = _tableCache.get(key);
      if (columns) {
        for (const col of columns) {
          suggestions.push({
            label: col.name,
            kind: monaco.languages.CompletionItemKind.Field,
            insertText: col.name,
            detail: col.data_type || '',
            range,
            sortText: '0_' + col.name,
          });
        }
        return;
      }
    }

    // Try as table name directly
    for (const [key, columns] of _tableCache) {
      const parts = key.split('.');
      const tableName = parts[parts.length - 1];
      if (tableName.toLowerCase() === alias.toLowerCase()) {
        for (const col of columns) {
          suggestions.push({
            label: col.name,
            kind: monaco.languages.CompletionItemKind.Field,
            insertText: col.name,
            detail: col.data_type || '',
            range,
            sortText: '0_' + col.name,
          });
        }
        return;
      }
    }
  }

  function _addSchemaTableSuggestions(suggestions, range, schemaName) {
    const tables = _getAvailableTables();
    for (const t of tables) {
      if (t.schema.toLowerCase() === schemaName.toLowerCase()) {
        suggestions.push({
          label: t.name,
          kind: monaco.languages.CompletionItemKind.Struct,
          insertText: t.name,
          detail: t.type || 'TABLE',
          range,
          sortText: '0_' + t.name,
        });
      }
    }
  }

  function _addSnippetSuggestions(suggestions, range) {
    if (!_dialectData?.snippets) return;
    for (const snip of _dialectData.snippets) {
      suggestions.push({
        label: snip.label,
        kind: monaco.languages.CompletionItemKind.Snippet,
        insertText: snip.insertText,
        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        detail: 'Snippet',
        range,
        sortText: '5_' + snip.label,
      });
    }
  }

  // ---- Helpers ----

  function _getAvailableTables() {
    const tables = [];
    for (const [connId] of AppState.connections) {
      const connEl = document.querySelector(`[data-conn="${connId}"]`);
      if (!connEl) continue;
      connEl.querySelectorAll('[data-schema]').forEach(schemaEl => {
        const schema = schemaEl.dataset.schema;
        schemaEl.querySelectorAll('[data-table]').forEach(tableEl => {
          tables.push({ connId, schema, name: tableEl.dataset.table, type: 'TABLE' });
        });
      });
    }
    return tables;
  }

  /**
   * Parse table aliases from SQL text.
   * FROM table alias, FROM table AS alias, JOIN table alias
   */
  function _parseAliases(sql) {
    const aliases = new Map();
    const connId = AppState.activeConn;
    if (!connId) return aliases;

    const conn = AppState.connections.get(connId);
    const defaultSchema = conn?.schemas?.[0] || 'main';

    const re = /\b(?:FROM|JOIN)\s+(?:"?(\w+)"?\.)?"?(\w+)"?\s+(?:AS\s+)?(\w+)/gi;
    let m;
    while ((m = re.exec(sql)) !== null) {
      const schema = m[1] || defaultSchema;
      const table = m[2];
      const alias = m[3];
      if (_isSqlKeyword(alias)) continue;
      aliases.set(alias.toLowerCase(), { connId, schema, table });
    }

    return aliases;
  }

  function _isSqlKeyword(word) {
    const kws = new Set([
      'WHERE', 'ON', 'AND', 'OR', 'SET', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
      'CROSS', 'FULL', 'JOIN', 'GROUP', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET',
      'UNION', 'EXCEPT', 'INTERSECT', 'AS', 'SELECT', 'FROM', 'INTO', 'VALUES',
      'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TABLE', 'INDEX',
      'VIEW', 'IF', 'EXISTS', 'NOT', 'NULL', 'BETWEEN', 'IN', 'LIKE', 'CASE',
      'WHEN', 'THEN', 'ELSE', 'END', 'NATURAL', 'USING',
    ]);
    return kws.has(word.toUpperCase());
  }

  /**
   * Generate a short alias from a table name.
   * user_orders → uo, UserProfile → up, orders → o
   */
  function _generateAlias(tableName) {
    if (tableName.includes('_')) {
      return tableName.split('_').map(s => s[0] || '').join('').toLowerCase();
    }
    const uppers = tableName.match(/[A-Z]/g);
    if (uppers && uppers.length > 1) {
      return uppers.join('').toLowerCase();
    }
    return tableName[0].toLowerCase();
  }

  return {
    init, setDialect, getDialect, setCachedColumns,
    SUPPORTED_DIALECTS,
  };
})();
