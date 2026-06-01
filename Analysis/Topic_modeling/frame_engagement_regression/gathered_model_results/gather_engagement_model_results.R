suppressPackageStartupMessages({
  library(stats)
})

args <- commandArgs(trailingOnly = TRUE)

default_input_csv <- file.path(getwd(), "Datasets", "gl-cl-w-topics-FINAL.csv")
default_output_dir <- file.path(getwd(), "Analysis", "Topic_modeling", "frame_engagement_regression", "gathered_model_results")
frame_column <- "frame"
reference_frame <- "Nature/Tourism"
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

fmt <- function(x, digits = 3) {
  ifelse(is.na(x), "NA", formatC(x, format = "f", digits = digits))
}

percent_effect <- function(model, term) {
  coefs <- as.data.frame(summary(model)$coefficients)
  coefs$term <- rownames(coefs)
  row <- coefs[coefs$term == term, ]
  if (nrow(row) == 0) {
    return(NULL)
  }

  estimate <- row[[1]]
  std_error <- row[[2]]
  t_crit <- qt(0.975, df.residual(model))
  ci_low <- estimate - t_crit * std_error
  ci_high <- estimate + t_crit * std_error
  data.frame(
    term = term,
    estimate = estimate,
    std_error = std_error,
    p_value = row[[4]],
    percent_estimate = (exp(estimate) - 1) * 100,
    percent_ci_low = (exp(ci_low) - 1) * 100,
    percent_ci_high = (exp(ci_high) - 1) * 100,
    stringsAsFactors = FALSE
  )
}

print_model_block <- function(title, model, focal_terms = character(0)) {
  cat("\n", paste(rep("=", 80), collapse = ""), "\n", sep = "")
  cat(title, "\n")
  cat(paste(rep("=", 80), collapse = ""), "\n\n", sep = "")
  cat("Formula:", deparse(formula(model)), "\n")
  cat("Rows used:", nobs(model), "\n")
  cat("Adjusted R-squared:", fmt(summary(model)$adj.r.squared), "\n\n")

  if (length(focal_terms) > 0) {
    cat("Interpretable log-coefficient transformations\n")
    for (term in focal_terms) {
      effect <- percent_effect(model, term)
      if (is.null(effect)) {
        next
      }
      cat(
        "  ", term,
        ": coefficient = ", fmt(effect$estimate),
        ", percent difference = ", fmt(effect$percent_estimate, 1), "%",
        ", 95% CI = [", fmt(effect$percent_ci_low, 1), "%, ", fmt(effect$percent_ci_high, 1), "%]",
        ", p = ", format.pval(effect$p_value, digits = 4, eps = 0.0001),
        "\n",
        sep = ""
      )
    }
    cat("\n")
  }

  print(summary(model))
  cat("\n")
}

df <- read.csv(input_csv, stringsAsFactors = FALSE, check.names = FALSE)
required <- c(frame_column, "view_count", "comment_count", "channel_subscriber_count")
missing_cols <- setdiff(required, names(df))
if (length(missing_cols) > 0) {
  stop(paste("Missing required columns:", paste(missing_cols, collapse = ", ")))
}

df$frame <- trimws(df[[frame_column]])
df <- subset(df, nzchar(frame))

df$view_count_num <- parse_numeric(df$view_count)
df$comment_count_num <- parse_numeric(df$comment_count)
df$channel_subscriber_count_num <- parse_numeric(df$channel_subscriber_count)
if ("video_like_count" %in% names(df)) {
  df$video_like_count_num <- parse_numeric(df$video_like_count)
} else {
  warning("No video_like_count column found. Likes models will be skipped.")
  df$video_like_count_num <- NA_real_
}

df$log_views <- log1p(df$view_count_num)
df$log_comments <- log1p(df$comment_count_num)
df$log_likes <- log1p(df$video_like_count_num)
df$is_geopolitical <- ifelse(df$frame == geopolitical_frame, 1, 0)

frame_levels <- names(sort(table(df$frame), decreasing = TRUE))
if (!reference_frame %in% frame_levels) {
  stop(paste(
    "Reference frame not found:",
    reference_frame,
    "Available frames:",
    paste(frame_levels, collapse = ", ")
  ))
}
if (!geopolitical_frame %in% frame_levels) {
  stop(paste(
    "Geopolitical frame not found:",
    geopolitical_frame,
    "Available frames:",
    paste(frame_levels, collapse = ", ")
  ))
}

all_frame_df <- df
all_frame_df$frame <- factor(all_frame_df$frame, levels = c(reference_frame, setdiff(frame_levels, reference_frame)))
all_frame_likes_df <- subset(all_frame_df, !is.na(log_likes))

geopolitics_df <- df
geopolitics_df$binary_frame <- ifelse(geopolitics_df$frame == geopolitical_frame, geopolitical_frame, "Other Frames")
geopolitics_df$binary_frame <- factor(geopolitics_df$binary_frame, levels = c("Other Frames", geopolitical_frame))
geopolitics_likes_df <- subset(geopolitics_df, !is.na(log_likes))

subscriber_df <- df
subscriber_df$log_subscribers <- log1p(subscriber_df$channel_subscriber_count_num)
subscriber_likes_df <- subscriber_df

models <- list(
  all_frames_views = lm(log_views ~ frame, data = all_frame_df),
  all_frames_comments = lm(log_comments ~ frame, data = all_frame_df),
  all_frames_likes = lm(log_likes ~ frame, data = all_frame_likes_df),
  geopolitics_vs_other_views = lm(log_views ~ binary_frame, data = geopolitics_df),
  geopolitics_vs_other_comments = lm(log_comments ~ binary_frame, data = geopolitics_df),
  geopolitics_vs_other_likes = lm(log_likes ~ binary_frame, data = geopolitics_likes_df),
  subscriber_control_views = lm(log_views ~ is_geopolitical + log_subscribers, data = subscriber_df),
  subscriber_control_comments = lm(log_comments ~ is_geopolitical + log_subscribers, data = subscriber_df),
  subscriber_control_likes = lm(log_likes ~ is_geopolitical + log_subscribers, data = subscriber_likes_df)
)

output_path <- file.path(output_dir, "engagement-regression-model-results.txt")

sink(output_path)
cat("Engagement Regression Model Results\n")
cat("Input CSV:", input_csv, "\n")
cat("Generated:", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"), "\n\n")
cat("This file gathers 9 models:\n")
cat("  1-3. All frames compared with Nature/Tourism, for views, comments, and likes.\n")
cat("  4-6. Geopolitics compared with all other frames, for views, comments, and likes.\n")
cat("  7-9. Geopolitics compared with all other frames with log subscribers controlled, for views, comments, and likes.\n\n")
cat("Dependent variables are log1p transformed engagement variables.\n")
cat("Subscriber control is log1p(channel_subscriber_count).\n")
cat("95% confidence intervals for coefficients use the t-distribution critical value with df.residual(model), not a fixed z = 1.96.\n")
cat("Percent difference rows are computed as (exp(coefficient) - 1) * 100, and their CIs are exponentiated from the coefficient bounds.\n")
cat("Reference frame for all-frame models:", reference_frame, "\n")
cat("Reference group for geopolitics models: Other Frames\n\n")

all_frame_focal_terms <- grep("^frame", names(coef(models$all_frames_views)), value = TRUE)
print_model_block(
  "1. All frames model: views, reference = Nature/Tourism",
  models$all_frames_views,
  all_frame_focal_terms
)
print_model_block(
  "2. All frames model: comments, reference = Nature/Tourism",
  models$all_frames_comments,
  grep("^frame", names(coef(models$all_frames_comments)), value = TRUE)
)
print_model_block(
  "3. All frames model: likes, reference = Nature/Tourism",
  models$all_frames_likes,
  grep("^frame", names(coef(models$all_frames_likes)), value = TRUE)
)
print_model_block(
  "4. Geopolitics vs all other frames: views",
  models$geopolitics_vs_other_views,
  "binary_frameGeopolitics"
)
print_model_block(
  "5. Geopolitics vs all other frames: comments",
  models$geopolitics_vs_other_comments,
  "binary_frameGeopolitics"
)
print_model_block(
  "6. Geopolitics vs all other frames: likes",
  models$geopolitics_vs_other_likes,
  "binary_frameGeopolitics"
)
print_model_block(
  "7. Subscriber-controlled geopolitics model: views",
  models$subscriber_control_views,
  "is_geopolitical"
)
print_model_block(
  "8. Subscriber-controlled geopolitics model: comments",
  models$subscriber_control_comments,
  "is_geopolitical"
)
print_model_block(
  "9. Subscriber-controlled geopolitics model: likes",
  models$subscriber_control_likes,
  "is_geopolitical"
)
sink()

cat("Saved gathered model results to:", output_path, "\n")
