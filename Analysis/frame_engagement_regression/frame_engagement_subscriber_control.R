suppressPackageStartupMessages({
  library(stats)
})

args <- commandArgs(trailingOnly = TRUE)

default_input_csv <- file.path(getwd(), "Datasets", "gl-cl-w-topics-FINAL.csv")
default_output_dir <- file.path(getwd(), "Analysis", "Topic_modeling", "frame_engagement_regression")
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

tidy_lm <- function(model, model_name, outcome) {
  coef_table <- as.data.frame(summary(model)$coefficients)
  coef_table$term <- rownames(coef_table)
  rownames(coef_table) <- NULL
  names(coef_table)[1:4] <- c("estimate", "std_error", "t_value", "p_value")
  coef_table$model <- model_name
  coef_table$outcome <- outcome
  coef_table$ci_low <- coef_table$estimate - 1.96 * coef_table$std_error
  coef_table$ci_high <- coef_table$estimate + 1.96 * coef_table$std_error
  coef_table[, c("model", "outcome", "term", "estimate", "std_error", "t_value", "p_value", "ci_low", "ci_high")]
}

extract_geopolitical_effect <- function(tidy_df, model_name, outcome) {
  coef_term <- "is_geopolitical"
  row <- tidy_df[
    tidy_df$model == model_name &
      tidy_df$outcome == outcome &
      tidy_df$term == coef_term,
  ]
  if (nrow(row) == 0) {
    return(data.frame(
      model = model_name,
      outcome = outcome,
      comparison = "Geopolitics vs all other frames",
      estimate = NA_real_,
      std_error = NA_real_,
      p_value = NA_real_,
      ci_low = NA_real_,
      ci_high = NA_real_
    ))
  }
  data.frame(
    model = model_name,
    outcome = outcome,
    comparison = "Geopolitics vs all other frames",
    estimate = row$estimate,
    std_error = row$std_error,
    p_value = row$p_value,
    ci_low = row$ci_low,
    ci_high = row$ci_high
  )
}

format_num <- function(x, digits = 3) {
  ifelse(is.na(x), "NA", formatC(x, format = "f", digits = digits))
}

compute_vif <- function(model) {
  terms <- attr(model$terms, "term.labels")
  vif_values <- sapply(terms, function(term) {
    if (term == "is_geopolitical") return(NA_real_)
    response <- model$model[[term]]
    if (is.factor(response) || is.character(response)) return(NA_real_)
    other_terms <- setdiff(terms, term)
    if (length(other_terms) == 0) return(NA_real_)
    formula <- as.formula(paste(term, "~", paste(other_terms, collapse = " + ")))
    r2 <- summary(lm(formula, data = model$model))$r.squared
    1 / (1 - r2)
  })
  data.frame(term = terms, vif = vif_values, stringsAsFactors = FALSE)
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
  warning("No video_like_count column found. Skipping likes model.")
  df$video_like_count_num <- NA_real_
}
## published_month and channel video-count controls removed (over-control)

model_df <- subset(
  df,
  nzchar(frame) &
    !is.na(view_count_num) &
    !is.na(comment_count_num) &
    !is.na(channel_subscriber_count_num)
)

if (nrow(model_df) == 0) {
  stop("No rows remain after cleaning required regression columns.")
}

model_df$log_views <- log1p(model_df$view_count_num)
model_df$log_comments <- log1p(model_df$comment_count_num)
model_df$log_subscribers <- log1p(model_df$channel_subscriber_count_num)
model_df$log_likes <- log1p(model_df$video_like_count_num)
model_df$is_geopolitical <- ifelse(model_df$frame == geopolitical_frame, 1, 0)

if (!any(model_df$is_geopolitical == 1)) {
  stop(paste("No rows found for geopolitical frame:", geopolitical_frame))
}

views_frame_only <- lm(log_views ~ is_geopolitical, data = model_df)
views_subscriber_control <- lm(
  log_views ~ is_geopolitical + log_subscribers,
  data = model_df
)
comments_frame_only <- lm(log_comments ~ is_geopolitical, data = model_df)
comments_subscriber_control <- lm(
  log_comments ~ is_geopolitical + log_subscribers,
  data = model_df
)
likes_df <- subset(model_df, !is.na(log_likes))
likes_frame_only <- if (nrow(likes_df) > 0) lm(log_likes ~ is_geopolitical, data = likes_df) else NULL
likes_subscriber_control <- if (nrow(likes_df) > 0) lm(log_likes ~ is_geopolitical + log_subscribers, data = likes_df) else NULL

views_vif <- compute_vif(views_subscriber_control)
comments_vif <- compute_vif(comments_subscriber_control)
likes_vif <- if (!is.null(likes_subscriber_control)) compute_vif(likes_subscriber_control) else NULL

all_tidy <- rbind(
  tidy_lm(views_frame_only, "views_frame_only", "log_views"),
  tidy_lm(views_subscriber_control, "views_subscriber_control", "log_views"),
  tidy_lm(comments_frame_only, "comments_frame_only", "log_comments"),
  tidy_lm(comments_subscriber_control, "comments_subscriber_control", "log_comments"),
  if (!is.null(likes_frame_only)) tidy_lm(likes_frame_only, "likes_frame_only", "log_likes") else NULL,
  if (!is.null(likes_subscriber_control)) tidy_lm(likes_subscriber_control, "likes_subscriber_control", "log_likes") else NULL
)

geopolitical_effects <- rbind(
  extract_geopolitical_effect(all_tidy, "views_frame_only", "log_views"),
  extract_geopolitical_effect(all_tidy, "views_subscriber_control", "log_views"),
  extract_geopolitical_effect(all_tidy, "comments_frame_only", "log_comments"),
  extract_geopolitical_effect(all_tidy, "comments_subscriber_control", "log_comments"),
  if (!is.null(likes_frame_only)) extract_geopolitical_effect(all_tidy, "likes_frame_only", "log_likes") else NULL,
  if (!is.null(likes_subscriber_control)) extract_geopolitical_effect(all_tidy, "likes_subscriber_control", "log_likes") else NULL
)
geopolitical_effects$percent_difference <- (exp(geopolitical_effects$estimate) - 1) * 100
geopolitical_effects$ci_low_percent <- (exp(geopolitical_effects$ci_low) - 1) * 100
geopolitical_effects$ci_high_percent <- (exp(geopolitical_effects$ci_high) - 1) * 100

coefficients_path <- file.path(output_dir, "frame-engagement-subscriber-control-coefficients.csv")
summary_path <- file.path(output_dir, "frame-engagement-subscriber-control-summary.txt")

write.csv(all_tidy, coefficients_path, row.names = FALSE)

sink(summary_path)
cat("Frame engagement subscriber-control regression\n")
cat("Input CSV:", input_csv, "\n")
cat("Rows used:", nrow(model_df), "\n")
cat("Comparison: Geopolitics vs all other frames\n")
cat("Subscriber control: log1p(channel_subscriber_count)\n")
cat("No channel video-count or publication-month controls (removed)\n\n")

cat("Geopolitics effect relative to all other frames\n")
for (i in seq_len(nrow(geopolitical_effects))) {
  row <- geopolitical_effects[i, ]
  cat(
    row$model,
    "|", row$outcome,
    "| log coefficient:", format_num(row$estimate),
    "| approx percent difference:", format_num(row$percent_difference, 1), "%",
    "| p:", format_num(row$p_value, 4),
    "\n"
  )
}

cat("\nModel fit comparison\n")
cat("Views frame-only adjusted R2:", format_num(summary(views_frame_only)$adj.r.squared), "\n")
cat("Views subscriber-control adjusted R2 (subs only):", format_num(summary(views_subscriber_control)$adj.r.squared), "\n")
cat("Comments frame-only adjusted R2:", format_num(summary(comments_frame_only)$adj.r.squared), "\n")
cat("Comments subscriber-control adjusted R2 (subs only):", format_num(summary(comments_subscriber_control)$adj.r.squared), "\n")
if (!is.null(likes_frame_only)) {
  cat("Likes frame-only adjusted R2:", format_num(summary(likes_frame_only)$adj.r.squared), "\n")
  cat("Likes subscriber-control adjusted R2 (subs only):", format_num(summary(likes_subscriber_control)$adj.r.squared), "\n")
}
cat("\n")
cat("Multicollinearity diagnostics (variance inflation factors, numeric predictors only):\n")
cat("Views subscriber-control VIFs:\n")
print(views_vif)
cat("Comments subscriber-control VIFs:\n")
print(comments_vif)
if (!is.null(likes_vif)) {
  cat("Likes subscriber-control VIFs:\n")
  print(likes_vif)
}
cat("\n")

cat("Full model summaries\n\n")
cat("Views geopolitical vs other, frame-only\n")
print(summary(views_frame_only))
cat("\nViews geopolitical vs other, subscriber-control\n")
print(summary(views_subscriber_control))
cat("\nComments geopolitical vs other, frame-only\n")
print(summary(comments_frame_only))
cat("\nComments geopolitical vs other, subscriber-control\n")
print(summary(comments_subscriber_control))
if (!is.null(likes_frame_only)) {
  cat("\nLikes geopolitical vs other, frame-only\n")
  print(summary(likes_frame_only))
  cat("\nLikes geopolitical vs other, subscriber-control\n")
  print(summary(likes_subscriber_control))
}
sink()

cat("Input CSV:", input_csv, "\n")
cat("Rows used:", nrow(model_df), "\n")
cat("Comparison: Geopolitics vs all other frames\n")
cat("Saved coefficients CSV to:", coefficients_path, "\n")
cat("Saved summary to:", summary_path, "\n")
