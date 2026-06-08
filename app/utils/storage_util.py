import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from structlog import get_logger
import asyncio

# Load environment variables from .env file
load_dotenv()

logger = get_logger(__name__)


async def upload_to_cloud(file_bytes: bytes, filename: str) -> str:
    """
    Upload file bytes to Cloudinary and return the file URL.
    Runs the synchronous Cloudinary upload in a thread pool to avoid blocking.

    Args:
        file_bytes: The file content as bytes
        filename: The name of the file

    Returns:
        The Cloudinary URL of the uploaded file

    Raises:
        Exception: If upload fails
    """
    def _sync_upload():
        try:
            # Get Cloudinary configuration from environment
            cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
            api_key = os.getenv("CLOUDINARY_API_KEY")
            api_secret = os.getenv("CLOUDINARY_API_SECRET")

            if not all([cloud_name, api_key, api_secret]):
                raise ValueError("Missing Cloudinary configuration. Check CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET environment variables.")

            # Configure Cloudinary
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret
            )

            # Upload file to Cloudinary
            upload_result = cloudinary.uploader.upload(
                file_bytes,
                public_id=f"uploads/{filename}",
                resource_type="auto"
            )

            file_url = upload_result.get("secure_url")

            logger.info(f"Successfully uploaded {filename} to Cloudinary: {file_url}")
            return file_url

        except Exception as e:
            logger.error(f"Cloudinary upload failed for {filename}: {str(e)}")
            raise Exception(f"Failed to upload file to Cloudinary: {str(e)}")

    try:
        # Run the synchronous upload in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        file_url = await loop.run_in_executor(None, _sync_upload)
        return file_url
    except Exception as e:
        logger.error(f"Cloudinary upload failed for {filename}: {str(e)}")
        raise Exception(f"Failed to upload file to Cloudinary: {str(e)}")
