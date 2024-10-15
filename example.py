# This is an automatically generated code sample.
# To make this code sample work in your Oracle Cloud tenancy,
# please replace the values for any parameters whose current values do not fit
# your use case (such as resource IDs, strings containing ‘EXAMPLE’ or ‘unique_id’, and
# boolean, number, and enum parameters with values not fitting your use case).

import oci

# Create a default config using DEFAULT profile in default location
# Refer to
# https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm#SDK_and_CLI_Configuration_File
# for more info
config = oci.config.from_file()


# Initialize service client with default config file
ai_language_client = oci.ai_language.AIServiceLanguageClient(config)


# Send the request to service, some parameters are not required, see API
# d oc for more info
batch_language_translation_response = ai_language_client.batch_language_translation(
    batch_language_translation_details=oci.ai_language.models.BatchLanguageTranslationDetails(
        documents=[
            oci.ai_language.models.TextDocument(
                key="EXAMPLE-key-Value",
                text="EXAMPLE-text-Value",
                language_code="EXAMPLE-languageCode-Value")],
        compartment_id="ocid1.test.oc1..<unique_ID>EXAMPLE-compartmentId-Value",
        target_language_code="EXAMPLE-targetLanguageCode-Value"),
    opc_request_id="UEFNLQEL0PID3M4DYU5T<unique_ID>")

# Get the data from response
print(batch_language_translation_response.data)
