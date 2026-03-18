<%*
// 模板启动器 - 快速选择模板
const template_options = [
  ["📅 会议纪要 (Meeting)", "Template_Meeting"],
  ["🚀 项目主页 (Project)", "Template_Project"],
  ["📝 原子笔记 (Note)", "Template_Note"],
  ["🛠️ 问题排查 (Bugfix)", "Template_Bugfix"],
  ["🔍 审计项目 (Audit)", "Template_Audit_Project"],
  ["📚 研究笔记 (Research)", "Template_Research"],
  ["🎤 访谈记录 (Interview)", "Template_Interview"]
];

// 弹窗让用户选择
const selected_template = await tp.system.suggester(
  item => item[0], 
  template_options
);

// 逻辑处理
if (selected_template) {
  const template_file = tp.file.find_tfile(selected_template[1]);
  
  if (template_file) {
    tR += await tp.file.include(template_file);
  } else {
    new Notice("❌ 找不到模板文件: " + selected_template[1]);
  }
} else {
  // 默认简单模板
  tR += "---\n";
  tR += "created: " + tp.file.creation_date("YYYY-MM-DD HH:mm") + "\n";
  tR += "---\n\n";
  tR += "# " + tp.file.title + "\n\n";
  tR += tp.file.cursor();
}
%>