"""
SparkML Feature Engineering + Profit-Margin Regression
========================================================

Reprocesses the same cleaning/feature-engineering steps from
notebooks/01_data_cleaning.ipynb through Spark DataFrames + Spark MLlib
instead of pandas/scikit-learn, and trains a regression model to predict
profit margin from order characteristics.

This runs on a LOCAL Spark session (`local[*]`) -- it is not connected to a
real multi-node cluster. That's a normal, honest way to demonstrate Spark/
SparkML competency without needing cluster infrastructure, and it's worth
saying exactly that if asked in an interview: the DataFrame API, MLlib
Pipeline structure, and distributed-style groupBy/join operations are
identical to what you'd run on a real cluster -- only the number of
executors changes.

Usage:
    python sparkml_pipeline.py --orders ../data/processed/orders.csv --products ../data/processed/products.csv
"""

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler
from pyspark.ml.regression import GBTRegressor, LinearRegression
from pyspark.ml.evaluation import RegressionEvaluator


def get_spark(app_name="retail-sparkml") -> SparkSession:
    return (
        SparkSession.builder.appName(app_name)
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")  # small dataset, no need for 200 default partitions
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )


def load_and_engineer(spark: SparkSession, orders_path: str, products_path: str):
    orders = spark.read.csv(orders_path, header=True, inferSchema=True)
    products = spark.read.csv(products_path, header=True, inferSchema=True)

    df = orders.join(products.select("product_id", "category", "sub_category"), on="product_id", how="left")

    # same feature logic as the pandas notebook, expressed as Spark
    # transformations -- this is the "distributed processing" claim: these
    # operations parallelize across partitions/executors instead of running
    # single-threaded like the pandas equivalent
    df = df.withColumn("order_date", F.to_date("order_date"))
    df = df.withColumn("ship_date", F.to_date("ship_date"))
    df = df.dropna(subset=["sales", "profit", "discount", "quantity", "category", "ship_mode"])
    df = df.filter(F.col("sales") > 0)

    return df


def build_ml_pipeline(model_type: str = "gbt") -> Pipeline:
    cat_indexers = [
        StringIndexer(inputCol=c, outputCol=f"{c}_idx", handleInvalid="keep")
        for c in ["category", "ship_mode"]
    ]
    encoder = OneHotEncoder(
        inputCols=[f"{c}_idx" for c in ["category", "ship_mode"]],
        outputCols=[f"{c}_ohe" for c in ["category", "ship_mode"]],
    )
    assembler = VectorAssembler(
        inputCols=["sales", "quantity", "discount", "delivery_days", "category_ohe", "ship_mode_ohe"],
        outputCol="features",
    )
    if model_type == "gbt":
        model = GBTRegressor(featuresCol="features", labelCol="profit_margin", maxIter=50, maxDepth=5, seed=42)
    else:
        model = LinearRegression(featuresCol="features", labelCol="profit_margin")

    return Pipeline(stages=cat_indexers + [encoder, assembler, model])


def run(orders_path: str, products_path: str, model_type: str = "gbt"):
    spark = get_spark()
    spark.sparkContext.setLogLevel("ERROR")

    df = load_and_engineer(spark, orders_path, products_path)
    print(f"Loaded {df.count()} orders across {df.rdd.getNumPartitions()} partitions")

    # distributed-style aggregation, mirrors sql/02_business_queries.sql but
    # expressed as a Spark DataFrame groupBy instead of raw SQL
    print("\nAvg profit margin by discount tier (computed via Spark groupBy):")
    df.withColumn(
        "discount_tier",
        F.when(F.col("discount") == 0, "0%")
        .when(F.col("discount") <= 0.1, "1-10%")
        .when(F.col("discount") <= 0.2, "11-20%")
        .when(F.col("discount") <= 0.3, "21-30%")
        .otherwise("30%+"),
    ).groupBy("discount_tier").agg(
        F.round(F.avg("profit_margin"), 4).alias("avg_margin"),
        F.count("*").alias("orders"),
    ).orderBy("discount_tier").show()

    train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)
    pipeline = build_ml_pipeline(model_type)
    fitted = pipeline.fit(train_df)
    predictions = fitted.transform(test_df)

    evaluator_rmse = RegressionEvaluator(labelCol="profit_margin", predictionCol="prediction", metricName="rmse")
    evaluator_r2 = RegressionEvaluator(labelCol="profit_margin", predictionCol="prediction", metricName="r2")
    rmse = evaluator_rmse.evaluate(predictions)
    r2 = evaluator_r2.evaluate(predictions)

    print(f"\n{model_type.upper()} regression -- profit_margin prediction on held-out test set:")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  R^2:  {r2:.4f}")

    spark.stop()
    return rmse, r2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spark ML pipeline for profit-margin prediction")
    parser.add_argument("--orders", default="../data/processed/orders.csv")
    parser.add_argument("--products", default="../data/processed/products.csv")
    parser.add_argument("--model", choices=["gbt", "linear"], default="gbt")
    args = parser.parse_args()

    run(args.orders, args.products, args.model)
