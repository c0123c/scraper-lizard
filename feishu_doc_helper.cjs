const fs = require("fs");
const path = require("path");

const sdkCandidates = [
  "D:\\openclaw\\node_modules\\@larksuiteoapi\\node-sdk",
  "D:\\openclaw\\extensions\\feishu\\node_modules\\@larksuiteoapi\\node-sdk",
];

let Lark = null;
let lastSdkError = null;
for (const candidate of sdkCandidates) {
  try {
    Lark = require(candidate);
    break;
  } catch (err) {
    lastSdkError = err;
  }
}
if (!Lark) {
  throw lastSdkError || new Error("Could not load @larksuiteoapi/node-sdk");
}

const OPENCLAW_CONFIG = path.join(process.env.USERPROFILE || "", ".openclaw", "openclaw.json");

function loadConfig() {
  const raw = fs.readFileSync(OPENCLAW_CONFIG, "utf8");
  return JSON.parse(raw);
}

function getAccount(config, accountId) {
  const accounts = config?.channels?.feishu?.accounts || {};
  const selected = accountId || config?.channels?.feishu?.defaultAccount || "main";
  const account = accounts[selected];
  if (!account?.appId || !account?.appSecret) {
    throw new Error(`Feishu account not configured: ${selected}`);
  }
  return account;
}

function createClient(account) {
  return new Lark.Client({
    appId: account.appId,
    appSecret: account.appSecret,
    appType: Lark.AppType.SelfBuild,
    domain: Lark.Domain.Feishu,
  });
}

function parseToken(input, kind) {
  const value = String(input || "").trim();
  if (!value) return "";
  const docMatch = value.match(/\/docx\/([A-Za-z0-9]+)/i);
  if (docMatch) return docMatch[1];
  const folderMatch = value.match(/\/drive\/folder\/([A-Za-z0-9]+)/i);
  if (folderMatch) return folderMatch[1];
  if (kind === "doc" && /^[A-Za-z0-9]+$/.test(value)) return value;
  if (kind === "folder" && /^[A-Za-z0-9]+$/.test(value)) return value;
  return value;
}

function cleanBlocksForDescendant(blocks) {
  return (blocks || []).map((block) => {
    const { parent_id, ...cleanBlock } = block;
    if (cleanBlock.block_type === 32 && typeof cleanBlock.children === "string") {
      cleanBlock.children = [cleanBlock.children];
    }
    if (cleanBlock.block_type === 31 && cleanBlock.table) {
      const table = cleanBlock.table || {};
      const property = table.property || {};
      cleanBlock.table = {
        property: {
          ...(property.row_size !== undefined ? { row_size: property.row_size } : {}),
          ...(property.column_size !== undefined ? { column_size: property.column_size } : {}),
          ...(Array.isArray(property.column_width) ? { column_width: property.column_width } : {}),
        },
      };
    }
    return cleanBlock;
  });
}

async function convertMarkdown(client, markdown) {
  const res = await client.docx.document.convert({
    data: { content_type: "markdown", content: markdown },
  });
  if (res.code !== 0) {
    throw new Error(`convert failed: code=${res.code} msg=${res.msg || ""}`);
  }
  return {
    blocks: res.data?.blocks || [],
    firstLevelBlockIds: res.data?.first_level_block_ids || [],
  };
}

async function appendMarkdown(client, docToken, markdown) {
  const converted = await convertMarkdown(client, markdown);
  const descendants = cleanBlocksForDescendant(converted.blocks);
  if (!converted.firstLevelBlockIds.length || !descendants.length) {
    return { success: true, blocks_added: 0 };
  }
  const res = await client.docx.documentBlockDescendant.create({
    path: { document_id: docToken, block_id: docToken },
    data: {
      children_id: converted.firstLevelBlockIds,
      descendants,
      index: -1,
    },
  });
  if (res.code !== 0) {
    throw new Error(`append failed: code=${res.code} msg=${res.msg || ""}`);
  }
  return {
    success: true,
    blocks_added: converted.blocks.length,
    block_ids: (res.data?.children || []).map((b) => b.block_id),
  };
}

async function createDoc(client, title, folderToken) {
  const data = { title };
  if (folderToken) data.folder_token = folderToken;
  const res = await client.docx.document.create({ data });
  if (res.code !== 0) {
    throw new Error(`create failed: code=${res.code} msg=${res.msg || ""}`);
  }
  const docToken = res.data?.document?.document_id;
  if (!docToken) {
    throw new Error("Document creation returned no token");
  }
  return {
    document_id: docToken,
    title: res.data?.document?.title || title,
    url: `https://feishu.cn/docx/${docToken}`,
  };
}

async function main() {
  const raw = fs.readFileSync(0, "utf8");
  const input = JSON.parse(raw || "{}");
  const config = loadConfig();
  const account = getAccount(config, input.accountId);
  const client = createClient(account);

  let docToken = parseToken(input.docToken || input.docUrl, "doc");
  const folderToken = parseToken(input.folderToken || input.folderUrl, "folder");

  if (!docToken) {
    const created = await createDoc(client, input.title || "抓取汇总", folderToken || undefined);
    docToken = created.document_id;
    const appendRes = await appendMarkdown(client, docToken, input.markdown || "");
    process.stdout.write(
      JSON.stringify({
        ok: true,
        created: true,
        ...created,
        append: appendRes,
      }),
    );
    return;
  }

  const appendRes = await appendMarkdown(client, docToken, input.markdown || "");
  process.stdout.write(
    JSON.stringify({
      ok: true,
      created: false,
      document_id: docToken,
      url: `https://feishu.cn/docx/${docToken}`,
      append: appendRes,
    }),
  );
}

main().catch((err) => {
  const parts = [];
  parts.push(String(err && err.message ? err.message : err));
  if (err && err.response && err.response.data) {
    try {
      parts.push(JSON.stringify(err.response.data));
    } catch {}
  }
  process.stderr.write(parts.filter(Boolean).join("\n"));
  process.exit(1);
});
