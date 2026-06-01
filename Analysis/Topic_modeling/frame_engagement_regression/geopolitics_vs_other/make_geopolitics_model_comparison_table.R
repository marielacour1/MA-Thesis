suppressPackageStartupMessages({
  library(stats)
})

args <- commandArgs(trailingOnly = TRUE)

default_input_csv <- file.path(getwd(), "Datasets", "gl-cl-w-topics-FINAL.csv")
default_output_dir <- file.path(getwd(), "Analysis", "Topic_modeling", "frame_engagement_regression", "geopolitics_vs_other")
geopolitical_frame <- "Geopolitics"

input_csv <- if (length(args) >= 1) args[[1]] else default_input_csv
output_dir <- if (length(args) >= 2) args[[2]] else default_output_dir

input_csv <- normalizePath(input_csv, winslash = "/", mustWork = TRUE)
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

parse_numeric <- function(x) {
  x <- trimws(as.character(x))
  x <- gsub(",", "", x, fixed = TRUE)
  x[x == ""] <- NA
  suppressWarnings(as.numeric(x))
}

star <- function(p) {
  if (is.na(p)) return("")
  if (p < 0.001) return("***")
  if (p < 0.01) return("**")
  if (p < 0.05) return("*")
  ""
}

fmt <- function(x, digits = 3) {
  ifelse(is.na(x), "", formatC(x, format = "f", digits = digits))
}

fmt_int <- function(x) {
  formatC(x, format = "d", big.mark = ",")
}

html_escape <- function(x) {
  x <- gsub("&", "&amp;", x, fixed = TRUE)
  x <- gsub("<", "&lt;", x, fixed = TRUE)
  x <- gsub(">", "&gt;", x, fixed = TRUE)
  x
}

coef_cell <- function(model, term) {
  coefs <- as.data.frame(summary(model)$coefficients)
  coefs$term <- rownames(coefs)
  row <- coefs[coefs$term == term, ]
  if (nrow(row) == 0) return("")
  estimate <- row[[1]]
  p_value <- row[[4]]
  paste0(fmt(estimate), star(p_value))
}

se_cell <- function(model, term) {
  coefs <- as.data.frame(summary(model)$coefficients)
  coefs$term <- rownames(coefs)
  row <- coefs[coefs$term == term, ]
  if (nrow(row) == 0) return("")
  paste0("(", fmt(row[[2]]), ")")
}

percent_effect <- function(model, term) {
  coefs <- as.data.frame(summary(model)$coefficients)
  coefs$term <- rownames(coefs)
  row <- coefs[coefs$term == term, ]
  if (nrow(row) == 0) return(c(NA_real_, NA_real_, NA_real_))
  estimate <- row[[1]]
  std_error <- row[[2]]
  ci_low <- estimate - 1.96 * std_error
  ci_high <- estimate + 1.96 * std_error
  c(
    estimate = (exp(estimate) - 1) * 100,
    ci_low = (exp(ci_low) - 1) * 100,
    ci_high = (exp(ci_high) - 1) * 100
  )
}

model_stats <- function(model) {
  s <- summary(model)
  c(
    n = nobs(model),
    adj_r2 = s$adj.r.squared
  )
}

table_row <- function(label, values, class = "") {
  cells <- paste0("<td>", html_escape(values), "</td>", collapse = "")
  paste0("<tr class=\"", class, "\"><th>", html_escape(label), "</th>", cells, "</tr>")
}

df <- read.csv(input_csv, stringsAsFactors = FALSE, check.names = FALSE)
required <- c("frame", "view_count", "comment_count", "channel_subscriber_count")
missing_cols <- setdiff(required, names(df))
if (length(missing_cols) > 0) {
  stop(paste("Missing required columns:", paste(missing_cols, collapse = ", ")))
}

df$frame <- trimws(df$frame)
df$view_count_num <- parse_numeric(df$view_count)
df$comment_count_num <- parse_numeric(df$comment_count)
df$channel_subscriber_count_num <- parse_numeric(df$channel_subscriber_count)
if ("video_like_count" %in% names(df)) {
  df$video_like_count_num <- parse_numeric(df$video_like_count)
} else {
  warning("No video_like_count column found. Skipping likes models.")
  df$video_like_count_num <- NA_real_
}

df$is_geopolitical <- ifelse(df$frame == geopolitical_frame, 1, 0)
df$log_views <- log1p(df$view_count_num)
df$log_comments <- log1p(df$comment_count_num)
df$log_likes <- log1p(df$video_like_count_num)
df$log_subscribers <- log1p(df$channel_subscriber_count_num)

base_df <- subset(
  df,
  nzchar(frame) &
    !is.na(is_geopolitical) &
    !is.na(log_subscribers) &
    !is.na(log_views) &
    !is.na(log_comments)
)

if (nrow(base_df) == 0) {
  stop("No rows remain after cleaning required comparison-table columns.")
}
if (!any(base_df$is_geopolitical == 1)) {
  stop(paste("No rows found for geopolitical frame:", geopolitical_frame))
}

likes_df <- subset(base_df, !is.na(log_likes))

models <- list(
  views_frame_only = lm(log_views ~ is_geopolitical, data = base_df),
  views_subscriber_control = lm(log_views ~ is_geopolitical + log_subscribers, data = base_df),
  comments_frame_only = lm(log_comments ~ is_geopolitical, data = base_df),
  comments_subscriber_control = lm(log_comments ~ is_geopolitical + log_subscribers, data = base_df)
)

if (nrow(likes_df) > 0) {
  models$likes_frame_only <- lm(log_likes ~ is_geopolitical, data = likes_df)
  models$likes_subscriber_control <- lm(log_likes ~ is_geopolitical + log_subscribers, data = likes_df)
}

model_order <- names(models)
model_labels <- c(
  views_frame_only = "Views",
  views_subscriber_control = "Views",
  comments_frame_only = "Comments",
  comments_subscriber_control = "Comments",
  likes_frame_only = "Likes",
  likes_subscriber_control = "Likes"
)[model_order]
specification_labels <- ifelse(grepl("subscriber_control$", model_order), "Subscriber-adjusted", "Baseline")

geopolitical_percent_rows <- do.call(
  rbind,
  lapply(model_order, function(model_name) {
    effect <- percent_effect(models[[model_name]], "is_geopolitical")
    data.frame(
      model = model_name,
      outcome = model_labels[[model_name]],
      specification = specification_labels[model_order == model_name],
      percent_estimate = effect[["estimate"]],
      percent_ci_low = effect[["ci_low"]],
      percent_ci_high = effect[["ci_high"]],
      stringsAsFactors = FALSE
    )
  })
)

csv_path <- file.path(output_dir, "geopolitics-vs-other-model-comparison-percent-effects.csv")
write.csv(geopolitical_percent_rows, csv_path, row.names = FALSE)

stats <- lapply(models, model_stats)

header <- paste0(
  "<tr><th></th>",
  paste0("<th>(", seq_along(model_order), ")</th>", collapse = ""),
  "</tr>",
  "<tr><th>Outcome</th>",
  paste0("<th>", html_escape(model_labels), "</th>", collapse = ""),
  "</tr>",
  "<tr><th>Model</th>",
  paste0("<th>", specification_labels, "</th>", collapse = ""),
  "</tr>"
)

rows <- c(
  table_row(
    "Geopolitics coefficient",
    vapply(models, coef_cell, character(1), term = "is_geopolitical")
  ),
  table_row(
    "Percent difference",
    vapply(
      models,
      function(model) {
        effect <- percent_effect(model, "is_geopolitical")
        paste0(fmt(effect[["estimate"]], 1), "%")
      },
      character(1)
    )
  ),
  table_row(
    "95% CI",
    vapply(
      models,
      function(model) {
        effect <- percent_effect(model, "is_geopolitical")
        paste0("[", fmt(effect[["ci_low"]], 1), "%, ", fmt(effect[["ci_high"]], 1), "%]")
      },
      character(1)
    ),
    class = "se"
  ),
  table_row(
    "log(Subscribers + 1)",
    vapply(models, coef_cell, character(1), term = "log_subscribers")
  ),
  table_row(
    "Adjusted R2",
    vapply(stats, function(x) fmt(x[["adj_r2"]]), character(1))
  )
)

html <- paste0(
  "<!doctype html>\n",
  "<html>\n<head>\n<meta charset=\"utf-8\">\n",
  "<title>Geopolitics vs Other Frames Engagement Models</title>\n",
  "<style>\n",
  "body { font-family: 'Times New Roman', Times, serif; margin: 28px; color: #111; }\n",
  "table { border-collapse: collapse; font-size: 13px; min-width: 860px; }\n",
  "caption { caption-side: top; font-weight: bold; font-size: 16px; margin-bottom: 8px; }\n",
  "th, td { padding: 5px 10px; text-align: center; vertical-align: bottom; }\n",
  "th:first-child, td:first-child { text-align: left; }\n",
  "thead tr:first-child th { border-top: 1.5px solid #111; }\n",
  "thead tr:last-child th { border-bottom: 1px solid #111; }\n",
  "tbody tr:nth-last-child(2) th, tbody tr:nth-last-child(2) td { border-top: 1px solid #111; }\n",
  "tbody tr:last-child th, tbody tr:last-child td { border-bottom: 1.5px solid #111; }\n",
  ".se th, .se td { padding-top: 0; color: #333; }\n",
  ".note { max-width: 860px; font-size: 12px; margin-top: 8px; line-height: 1.35; }\n",
  "</style>\n",
  "</head>\n<body>\n",
  "<table>\n",
  "<caption>Geopolitics vs All Other Frames: Engagement Regression Models</caption>\n",
  "<thead>", header, "</thead>\n",
  "<tbody>\n", paste(rows, collapse = "\n"), "\n</tbody>\n",
  "</table>\n",
  "<div class=\"note\">",
  "Notes: Cells report OLS coefficients. ",
  "Percent differences transform the geopolitics coefficient as 100 * (exp(beta) - 1). ",
  "Dependent variables are log(views + 1), log(comments + 1), and log(likes + 1). ",
  "Geopolitics is compared against all other frames. ",
  "Frame-only and subscriber-control models use the same complete-case sample within each outcome. ",
  "* p &lt; .05; ** p &lt; .01; *** p &lt; .001.",
  "</div>\n",
  "</body>\n</html>\n"
)

html_path <- file.path(output_dir, "geopolitics-vs-other-model-comparison-table.html")
writeLines(html, html_path, useBytes = TRUE)

cat("Input CSV:", input_csv, "\n")
cat("Rows used for views/comments:", nrow(base_df), "\n")
cat("Rows used for likes:", nrow(likes_df), "\n")
cat("Saved stargazer-style HTML table to:", html_path, "\n")
cat("Saved percent-effect comparison CSV to:", csv_path, "\n")
